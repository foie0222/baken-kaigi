"""天候・馬場分析ツール.

天候・馬場状態が出走馬に与える影響を分析する。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# 馬場状態の区分
TRACK_CONDITIONS = ["良", "稍", "重", "不"]

# 馬場状態による影響係数（良を基準）
CONDITION_IMPACT = {
    "良": {"speed_factor": 1.0, "stamina_factor": 1.0},
    "稍": {"speed_factor": 0.98, "stamina_factor": 1.02},
    "重": {"speed_factor": 0.95, "stamina_factor": 1.05},
    "不": {"speed_factor": 0.90, "stamina_factor": 1.10},
}


@tool
def analyze_track_condition_impact(
    race_id: str,
    horse_id: str,
    horse_name: str,
) -> dict:
    """天候・馬場状態が馬に与える影響を分析する。

    馬場状態別の過去成績を分析し、現在の馬場状態が
    この馬にとって有利か不利かを判断する。

    Args:
        race_id: 対象レースID
        horse_id: 馬コード
        horse_name: 馬名（表示用）

    Returns:
        馬場影響分析結果（馬場状態別成績、適性評価、総合判断）
    """
    try:
        # レース情報取得
        race_info = _get_race_info(race_id)
        if "error" in race_info:
            return race_info

        current_condition = race_info.get("track_condition", "良")

        # 馬の過去成績取得
        performances = _get_performances(horse_id)
        if not performances:
            return {
                "warning": "過去成績データが見つかりませんでした",
                "horse_name": horse_name,
            }

        # 馬場状態別成績を分析
        condition_stats = _analyze_condition_stats(performances)

        # 現在の馬場への適性評価
        aptitude = _evaluate_aptitude(condition_stats, current_condition)

        # 脚質との関連性分析
        running_style_impact = _analyze_running_style_impact(performances, current_condition)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            horse_name, current_condition, condition_stats, aptitude, running_style_impact
        )

        return {
            "horse_name": horse_name,
            "current_condition": current_condition,
            "condition_stats": condition_stats,
            "aptitude": aptitude,
            "running_style_impact": running_style_impact,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze track condition impact: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze track condition impact: {e}")
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


def _get_performances(horse_id: str) -> list[dict]:
    """過去成績を取得する."""
    try:
        response = requests.get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": 20},
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("performances", data) if isinstance(data, dict) else data
        return []
    except requests.RequestException as e:
        logger.error(f"Failed to get performances for horse {horse_id}: {e}")
        return []


def _analyze_condition_stats(performances: list[dict]) -> dict:
    """馬場状態別成績を分析する."""
    stats = {cond: {"runs": 0, "wins": 0, "places": 0, "finishes": []} for cond in TRACK_CONDITIONS}

    for perf in performances:
        condition = perf.get("track_condition", "良")
        # 馬場状態を正規化（「良」「稍重」→「稍」など）
        normalized = _normalize_condition(condition)
        if normalized not in stats:
            continue

        finish = perf.get("finish_position", 0)
        if finish <= 0:
            continue

        stats[normalized]["runs"] += 1
        stats[normalized]["finishes"].append(finish)
        if finish == 1:
            stats[normalized]["wins"] += 1
        if finish <= 3:
            stats[normalized]["places"] += 1

    # 成績フォーマット
    result = {}
    for cond in TRACK_CONDITIONS:
        s = stats[cond]
        runs = s["runs"]
        if runs > 0:
            win_rate = round((s["wins"] / runs) * 100, 1)
            place_rate = round((s["places"] / runs) * 100, 1)
            avg_finish = round(sum(s["finishes"]) / runs, 1)
        else:
            win_rate = 0.0
            place_rate = 0.0
            avg_finish = 0.0

        result[cond] = {
            "runs": runs,
            "wins": s["wins"],
            "places": s["places"],
            "record": f"{s['wins']}-{s['places'] - s['wins']}-{runs - s['places']}",
            "win_rate": win_rate,
            "place_rate": place_rate,
            "avg_finish": avg_finish,
        }

    return result


def _normalize_condition(condition: str) -> str:
    """馬場状態を正規化する."""
    if "不" in condition:
        return "不"
    elif "重" in condition:
        return "重"
    elif "稍" in condition:
        return "稍"
    else:
        return "良"


def _evaluate_aptitude(condition_stats: dict, current_condition: str) -> dict:
    """現在の馬場への適性を評価する."""
    current_stats = condition_stats.get(current_condition, {})
    runs = current_stats.get("runs", 0)
    win_rate = current_stats.get("win_rate", 0.0)
    place_rate = current_stats.get("place_rate", 0.0)

    # 良馬場の成績と比較
    good_stats = condition_stats.get("良", {})
    good_win_rate = good_stats.get("win_rate", 0.0)
    good_place_rate = good_stats.get("place_rate", 0.0)

    # 適性評価
    if runs == 0:
        rating = "未知"
        comment = f"{current_condition}馬場での実績なし"
    elif win_rate > good_win_rate + 10:
        rating = "A"
        comment = f"{current_condition}馬場で好走傾向"
    elif win_rate > good_win_rate:
        rating = "B+"
        comment = f"{current_condition}馬場でも安定"
    elif win_rate >= good_win_rate - 10:
        rating = "B"
        comment = "馬場状態の影響は小さい"
    else:
        rating = "C"
        comment = f"{current_condition}馬場は苦手傾向"

    # 道悪巧者判定
    heavy_stats = condition_stats.get("重", {})
    bad_stats = condition_stats.get("不", {})
    heavy_runs = heavy_stats.get("runs", 0) + bad_stats.get("runs", 0)
    heavy_wins = heavy_stats.get("wins", 0) + bad_stats.get("wins", 0)

    is_mudder = False
    if heavy_runs >= 3:
        mudder_win_rate = (heavy_wins / heavy_runs) * 100 if heavy_runs > 0 else 0
        if mudder_win_rate > good_win_rate:
            is_mudder = True

    return {
        "rating": rating,
        "runs_on_condition": runs,
        "win_rate": win_rate,
        "place_rate": place_rate,
        "vs_good_condition": round(win_rate - good_win_rate, 1),
        "is_mudder": is_mudder,
        "comment": comment,
    }


def _analyze_running_style_impact(performances: list[dict], current_condition: str) -> dict:
    """脚質と馬場状態の関連性を分析する."""
    # 脚質別成績を集計
    style_stats = {}

    for perf in performances:
        style = perf.get("running_style", "不明")
        if style not in style_stats:
            style_stats[style] = {"runs": 0, "wins": 0}
        finish = perf.get("finish_position", 0)
        if finish <= 0:
            continue
        style_stats[style]["runs"] += 1
        if finish == 1:
            style_stats[style]["wins"] += 1

    # 最も多い脚質を特定
    main_style = "不明"
    max_runs = 0
    for style, stats in style_stats.items():
        if stats["runs"] > max_runs:
            max_runs = stats["runs"]
            main_style = style

    # 馬場状態による脚質有利不利
    style_advantage = _get_style_advantage(main_style, current_condition)

    return {
        "main_style": main_style,
        "style_advantage": style_advantage,
        "comment": _generate_style_comment(main_style, current_condition, style_advantage),
    }


def _get_style_advantage(style: str, condition: str) -> str:
    """脚質と馬場状態による有利不利を判定する."""
    # 一般的な傾向
    # 重馬場: 先行有利、差し追込不利
    # 良馬場: 差し追込が届きやすい

    if condition in ["重", "不"]:
        if style in ["逃げ", "先行"]:
            return "有利"
        elif style in ["差し", "追込"]:
            return "不利"
    elif condition == "良":
        if style in ["差し", "追込"]:
            return "やや有利"

    return "普通"


def _generate_style_comment(style: str, condition: str, advantage: str) -> str:
    """脚質コメントを生成する."""
    if advantage == "有利":
        return f"{condition}馬場は{style}馬に有利な展開が見込まれる"
    elif advantage == "不利":
        return f"{condition}馬場は{style}馬には厳しい条件"
    else:
        return f"脚質による影響は限定的"


def _generate_overall_comment(
    horse_name: str,
    current_condition: str,
    condition_stats: dict,
    aptitude: dict,
    running_style_impact: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # 適性評価
    rating = aptitude.get("rating", "")
    if rating == "A":
        parts.append(f"{horse_name}は{current_condition}馬場が得意")
    elif rating == "C":
        parts.append(f"{horse_name}は{current_condition}馬場で割引")
    else:
        parts.append(f"{horse_name}の{current_condition}馬場適性は普通")

    # 道悪巧者
    if aptitude.get("is_mudder"):
        parts.append("道悪巧者")

    # 脚質影響
    style_adv = running_style_impact.get("style_advantage", "普通")
    if style_adv == "有利":
        parts.append("脚質的にも有利")
    elif style_adv == "不利":
        parts.append("脚質的には不利")

    return "。".join(parts) + "。"
