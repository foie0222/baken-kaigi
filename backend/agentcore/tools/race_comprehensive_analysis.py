"""レース総合分析ツール.

レースの出走メンバーを総合的に分析し、各馬の評価と有力馬を特定する。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# 能力評価の閾値
SCORE_EXCELLENT = 80
SCORE_GOOD = 65

# オッズ評価の閾値
FAVORITE_ODDS_THRESHOLD = 5.0
VALUE_ODDS_THRESHOLD = 15.0

# 騎手評価の勝率閾値（%）
JOCKEY_WIN_RATE_EXCELLENT = 18.0
JOCKEY_WIN_RATE_GOOD = 12.0

# 馬体重評価の閾値（kg）
BODY_WEIGHT_IDEAL_MIN = 460.0
BODY_WEIGHT_IDEAL_MAX = 500.0
BODY_WEIGHT_ACCEPTABLE_MIN = 440.0
BODY_WEIGHT_ACCEPTABLE_MAX = 520.0


@tool
def analyze_race_comprehensive(race_id: str) -> dict:
    """レースの出走メンバーを総合的に分析し、各馬の評価と有力馬を特定する。

    出走全馬のクイック評価、能力比較ランキング、展開シナリオの予測、
    注目馬・穴馬の特定、危険な人気馬の警告を行う。

    Args:
        race_id: レースID (例: "20260125_05_11")

    Returns:
        総合分析結果（レース概要、出走馬評価、展開予想、注目馬、買い目提案）
    """
    try:
        # レース基本情報取得
        race_info = _get_race_info(race_id)
        if "error" in race_info:
            return race_info

        # 出走馬リスト取得
        runners = _get_runners(race_id)
        if not runners:
            return {"error": "出走馬データが取得できませんでした", "race_id": race_id}

        # 脚質データ取得
        running_styles = _get_running_styles(race_id)

        # オッズデータ取得
        odds_data = _get_current_odds(race_id)

        # 各馬の総合評価を計算
        runners_evaluation = _evaluate_all_runners(
            runners, running_styles, race_info
        )

        # ランキング順にソート
        runners_evaluation.sort(key=lambda x: x["overall_score"], reverse=True)
        for i, runner in enumerate(runners_evaluation, 1):
            runner["rank"] = i

        # 展開予想
        race_forecast = _predict_race_scenario(running_styles)

        # 注目馬の抽出
        notable_horses = _identify_notable_horses(runners_evaluation, odds_data)

        # 買い目提案
        betting_suggestion = _generate_betting_suggestion(notable_horses)

        # レース品質評価
        race_quality = _evaluate_race_quality(runners_evaluation, race_info)

        return {
            "race_id": race_id,
            "race_name": race_info.get("race_name", ""),
            "race_overview": {
                "venue": race_info.get("venue", ""),
                "distance": race_info.get("distance", 0),
                "track_type": race_info.get("track_type", ""),
                "grade": race_info.get("grade", ""),
                "total_runners": len(runners),
                "race_quality": race_quality,
            },
            "runners_evaluation": runners_evaluation,
            "race_forecast": race_forecast,
            "notable_horses": notable_horses,
            "betting_suggestion": betting_suggestion,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze race comprehensive: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze race comprehensive: {e}")
        return {"error": str(e)}


def _get_race_info(race_id: str) -> dict:
    """レース基本情報を取得する."""
    try:
        response = requests.get(
            f"{get_api_url()}/races/{race_id}",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return {"error": "レース情報が見つかりませんでした", "race_id": race_id}
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get race info: {e}")
        return {"error": f"レース情報取得エラー: {str(e)}"}


def _get_runners(race_id: str) -> list[dict]:
    """出走馬リストを取得する."""
    try:
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/runners",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("runners", [])
    except requests.RequestException as e:
        logger.error(f"Failed to get runners for race {race_id}: {e}")
        return []


def _get_running_styles(race_id: str) -> list[dict]:
    """脚質データを取得する."""
    try:
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/running-styles",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("running_styles", [])
    except requests.RequestException as e:
        logger.error(f"Failed to get running styles for race {race_id}: {e}")
        return []


def _get_current_odds(race_id: str) -> dict:
    """現在のオッズを取得する."""
    try:
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/odds/win",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        # 馬番をキーにしたマップに変換
        return {o.get("horse_number"): o.get("odds", 0) for o in data.get("odds", [])}
    except requests.RequestException as e:
        logger.error(f"Failed to get current odds for race {race_id}: {e}")
        return {}


def _evaluate_all_runners(
    runners: list[dict],
    running_styles: list[dict],
    race_info: dict,
) -> list[dict]:
    """全出走馬を評価する."""
    # 脚質マップ作成
    style_map = {r.get("horse_number"): r.get("running_style", "不明") for r in running_styles}

    evaluations = []
    for runner in runners:
        horse_number = runner.get("horse_number")
        horse_name = runner.get("horse_name", "")
        horse_id = runner.get("horse_id", "")

        # 各項目の評価を取得
        factors = _evaluate_horse_factors(horse_id, race_info, runner)

        # 強みと弱みの抽出
        strengths, weaknesses = _extract_strengths_weaknesses(
            factors, horse_number, style_map
        )

        # 総合スコア計算
        overall_score = _calculate_overall_score(factors)

        evaluations.append({
            "horse_number": horse_number,
            "horse_name": horse_name,
            "overall_score": overall_score,
            "rank": 0,  # 後でソート後に設定
            "strengths": strengths,
            "weaknesses": weaknesses,
            "key_factors": factors,
        })

    return evaluations


def _evaluate_horse_factors(horse_id: str, race_info: dict, runner: dict | None = None) -> dict:
    """馬の各要素を評価する."""
    runner = runner or {}
    factors = {
        "form": "B",
        "course_aptitude": "B",
        "jockey": "B",
        # trainer: JRA-VAN API に調教師成績エンドポイント（/trainers/{id}/stats 等）が
        # 存在しないため、現時点では評価不可。API 追加時に勝率ベース評価を実装予定。
        "trainer": "B",
        "weight": "B",
    }

    # 過去成績から評価
    try:
        response = requests.get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": 5},
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            performances = data.get("performances", [])
            if performances:
                factors["form"] = _evaluate_form_from_performances(performances)
    except requests.RequestException as e:
        logger.debug(f"Failed to get performances for horse {horse_id}: {e}")

    # コース適性評価
    try:
        response = requests.get(
            f"{get_api_url()}/horses/{horse_id}/course-aptitude",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            venue = race_info.get("venue", "")
            factors["course_aptitude"] = _evaluate_course_aptitude(data, venue)
    except requests.RequestException as e:
        logger.debug(f"Failed to get course aptitude for horse {horse_id}: {e}")

    # 騎手評価（JRA-VAN API から勝率を取得）
    jockey_id = runner.get("jockey_id", "")
    if jockey_id:
        factors["jockey"] = _evaluate_jockey(jockey_id)

    # 馬体重評価（runner の weight = 馬体重 kg）
    body_weight = runner.get("weight", 0)
    if body_weight and body_weight > 0:
        factors["weight"] = _evaluate_body_weight(float(body_weight))

    return factors


def _evaluate_form_from_performances(performances: list[dict]) -> str:
    """過去成績からフォームを評価する."""
    if not performances:
        return "C"

    finishes = [p.get("finish_position", 0) for p in performances if p.get("finish_position", 0) > 0]
    if not finishes:
        return "C"

    avg = sum(finishes) / len(finishes)
    in_money = sum(1 for f in finishes if f <= 3)

    if avg <= 3.0 and in_money >= 3:
        return "A"
    elif avg <= 5.0 and in_money >= 2:
        return "B"
    else:
        return "C"


def _evaluate_course_aptitude(data: dict, venue: str) -> str:
    """コース適性を評価する."""
    venue_stats = data.get("venue_stats", {}).get(venue, {})
    if not venue_stats:
        return "B"

    win_rate = venue_stats.get("win_rate", 0)
    in_money_rate = venue_stats.get("in_money_rate", 0)

    if win_rate >= 20 or in_money_rate >= 50:
        return "A"
    elif win_rate >= 10 or in_money_rate >= 30:
        return "B"
    else:
        return "C"


def _evaluate_jockey(jockey_id: str) -> str:
    """騎手を勝率ベースで評価する."""
    try:
        response = requests.get(
            f"{get_api_url()}/jockeys/{jockey_id}/stats",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            stats = response.json().get("stats", {})
            win_rate = stats.get("win_rate", 0.0)
            if win_rate >= JOCKEY_WIN_RATE_EXCELLENT:
                return "A"
            elif win_rate >= JOCKEY_WIN_RATE_GOOD:
                return "B"
            else:
                return "C"
    except requests.RequestException as e:
        logger.debug(f"Failed to get jockey stats for {jockey_id}: {e}")
    return "B"


def _evaluate_body_weight(weight_kg: float) -> str:
    """馬体重から状態を評価する.

    理想体重帯（460-500kg）を A、許容範囲（440-520kg）を B、
    それ以外を C と判定する。
    """
    if BODY_WEIGHT_IDEAL_MIN <= weight_kg <= BODY_WEIGHT_IDEAL_MAX:
        return "A"
    elif BODY_WEIGHT_ACCEPTABLE_MIN <= weight_kg <= BODY_WEIGHT_ACCEPTABLE_MAX:
        return "B"
    else:
        return "C"


def _extract_strengths_weaknesses(
    factors: dict,
    horse_number: int,
    style_map: dict,
) -> tuple[list[str], list[str]]:
    """強みと弱みを抽出する."""
    strengths = []
    weaknesses = []

    # 各要素を評価
    for key, value in factors.items():
        label = _get_factor_label(key)
        if value == "A":
            strengths.append(label)
        elif value == "C":
            weaknesses.append(label)

    # 枠順評価
    if horse_number <= 4:
        strengths.append("内枠")
    elif horse_number >= 14:
        weaknesses.append("外枠")

    # 脚質と展開の相性
    style = style_map.get(horse_number, "不明")
    if style == "逃げ":
        strengths.append("逃げ馬")
    elif style == "差し":
        strengths.append("末脚")

    return strengths[:4], weaknesses[:3]


def _get_factor_label(key: str) -> str:
    """要素キーをラベルに変換する."""
    labels = {
        "form": "好調",
        "course_aptitude": "コース実績",
        "jockey": "騎手◎",
        "trainer": "厩舎力",
        "weight": "馬体重良好",
    }
    return labels.get(key, key)


def _calculate_overall_score(factors: dict) -> int:
    """総合スコアを計算する."""
    score = 50  # ベーススコア

    # trainer は API 未対応のため除外
    weights = {
        "form": 25,
        "course_aptitude": 20,
        "jockey": 15,
        "weight": 10,
    }

    for key, weight in weights.items():
        grade = factors.get(key, "C")
        if grade == "A":
            score += weight
        elif grade == "C":
            score -= weight // 2
        # Bの場合は加算なし（平均的）

    return max(0, min(score, 100))


def _predict_race_scenario(running_styles: list[dict]) -> dict:
    """レース展開を予測する."""
    # 脚質分布を集計
    style_counts = {"逃げ": 0, "先行": 0, "差し": 0, "追込": 0}
    key_horse = None

    for style_data in running_styles:
        style = style_data.get("running_style", "不明")
        if style in style_counts:
            style_counts[style] += 1
        if style == "逃げ" and key_horse is None:
            key_horse = {
                "number": style_data.get("horse_number"),
                "name": style_data.get("horse_name"),
                "role": "逃げ馬",
            }

    # ペース予想
    escape_count = style_counts["逃げ"]
    if escape_count >= 3:
        predicted_pace = "ハイ"
        favorable_style = "差し"
        scenario = f"逃げ馬が{escape_count}頭いるため、ハイペース必至。差し馬有利の展開"
    elif escape_count <= 1:
        predicted_pace = "スロー"
        favorable_style = "先行"
        scenario = "逃げ馬が少なく、スローペース濃厚。前残りに注意"
    else:
        predicted_pace = "ミドル"
        favorable_style = "先行・差し"
        scenario = "平均的なペースで流れ、各馬の実力が問われる展開"

    return {
        "predicted_pace": predicted_pace,
        "favorable_running_style": favorable_style,
        "key_horse": key_horse,
        "scenario": scenario,
    }


def _identify_notable_horses(
    runners_evaluation: list[dict],
    odds_data: dict,
) -> dict:
    """注目馬を特定する."""
    top_picks = []
    value_picks = []
    danger_favorites = []

    for runner in runners_evaluation:
        horse_number = runner["horse_number"]
        horse_name = runner["horse_name"]
        score = runner["overall_score"]
        odds = odds_data.get(horse_number, 0)

        # 本命候補（スコア上位かつ人気馬）
        if score >= SCORE_EXCELLENT and runner["rank"] <= 3:
            top_picks.append({
                "number": horse_number,
                "name": horse_name,
                "reason": _generate_top_pick_reason(runner),
            })

        # 穴馬候補（スコアは高いがオッズが妙味あり）
        if score >= SCORE_GOOD and odds >= VALUE_ODDS_THRESHOLD:
            strengths = runner.get("strengths") or []
            strengths_reason = strengths[0] if strengths else "能力上位"
            value_picks.append({
                "number": horse_number,
                "name": horse_name,
                "reason": f"オッズ{odds}倍は妙味あり。{strengths_reason}",
            })

        # 危険な人気馬（人気だがスコアが低い）
        if odds > 0 and odds <= FAVORITE_ODDS_THRESHOLD and score < SCORE_GOOD:
            weaknesses = runner.get("weaknesses") or []
            reason = weaknesses[0] if weaknesses else "過剰人気の可能性"
            danger_favorites.append({
                "number": horse_number,
                "name": horse_name,
                "reason": f"オッズ{odds}倍も{reason}",
            })

    return {
        "top_picks": top_picks[:3],
        "value_picks": value_picks[:3],
        "danger_favorites": danger_favorites[:2],
    }


def _generate_top_pick_reason(runner: dict) -> str:
    """本命馬の推奨理由を生成する."""
    strengths = runner.get("strengths") or []
    if len(strengths) >= 2:
        return f"{strengths[0]}・{strengths[1]}で総合力No.1"
    elif strengths:
        return f"{strengths[0]}が光る"
    return "総合力で上位"


def _generate_betting_suggestion(notable_horses: dict) -> dict:
    """買い目提案を生成する."""
    top_picks = notable_horses.get("top_picks", [])
    value_picks = notable_horses.get("value_picks", [])
    danger_favorites = notable_horses.get("danger_favorites", [])

    # 信頼度判定
    if len(top_picks) >= 2 and not danger_favorites:
        confidence_level = "高"
        suggested_approach = "本命馬を軸にした馬連・馬単が有効"
        caution = ""
    elif len(top_picks) >= 1 and len(value_picks) >= 1:
        confidence_level = "中"
        suggested_approach = "本命-対抗の馬連・ワイドが妥当"
        caution = "穴馬も視野に入れた3連複も検討"
    else:
        confidence_level = "低"
        suggested_approach = "手広くワイド・3連複で"
        caution = "混戦模様のため本命不在。手広く構えたい"

    return {
        "confidence_level": confidence_level,
        "suggested_approach": suggested_approach,
        "caution": caution,
    }


def _evaluate_race_quality(runners_evaluation: list[dict], race_info: dict) -> str:
    """レースの品質を評価する."""
    grade = race_info.get("grade", "")

    # G1/G2は自動的にハイレベル
    if grade in ["G1", "G2"]:
        return "ハイレベル"

    # スコア分布で判定
    high_score_count = sum(1 for r in runners_evaluation if r["overall_score"] >= SCORE_GOOD)

    if high_score_count >= 5:
        return "ハイレベル"
    elif high_score_count >= 3:
        return "標準"
    else:
        return "混戦"
