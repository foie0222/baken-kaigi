"""前走レース分析ツール.

前走のレース内容を詳細に分析し、今回のレースへの影響を判断する。
"""

import logging

import requests
from strands import tool

from .jravan_client import cached_get, get_api_url

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30


@tool
def analyze_last_race_detail(
    horse_id: str,
    horse_name: str,
    race_id: str,
) -> dict:
    """前走のレース内容を詳細に分析する。

    前走のペース、位置取り、上がりタイム、着差などを分析し、
    今回のレースへの影響を判断する。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        race_id: 今回の対象レースID

    Returns:
        前走分析結果（レース内容、評価、今回への影響）
    """
    try:
        # 今回のレース情報取得
        current_race = _get_race_info(race_id)
        if "error" in current_race:
            return current_race

        # 過去成績取得（前走データ）
        performances = _get_performances(horse_id, limit=5)
        if not performances:
            return {
                "warning": "過去成績データが見つかりませんでした",
                "horse_name": horse_name,
            }

        last_race = performances[0]

        # 前走内容分析
        last_race_analysis = _analyze_last_race(last_race)

        # 前走からの変化点
        changes = _analyze_changes(last_race, current_race)

        # 前走成績の評価
        evaluation = _evaluate_last_race(last_race, performances)

        # 今回への影響判断
        impact = _assess_impact(last_race_analysis, changes, evaluation)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            horse_name, last_race_analysis, changes, evaluation, impact
        )

        return {
            "horse_name": horse_name,
            "last_race": last_race_analysis,
            "changes_from_last": changes,
            "evaluation": evaluation,
            "impact_on_current": impact,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze last race: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze last race: {e}")
        return {"error": str(e)}


def _get_race_info(race_id: str) -> dict:
    """レース基本情報を取得する."""
    try:
        response = cached_get(
            f"{get_api_url()}/races/{race_id}",
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return {"error": "レース情報が見つかりませんでした", "race_id": race_id}
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get race info: {e}")
        return {"error": f"レース情報取得エラー: {str(e)}"}


def _get_performances(horse_id: str, limit: int = 5) -> list[dict]:
    """過去成績を取得する."""
    try:
        response = cached_get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": limit},
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("performances", data) if isinstance(data, dict) else data
        return []
    except requests.RequestException as e:
        logger.error(f"Failed to get performances for horse {horse_id}: {e}")
        return []


def _analyze_last_race(last_race: dict) -> dict:
    """前走のレース内容を分析する."""
    finish = last_race.get("finish_position", 0)
    time = last_race.get("time", "")
    last_3f = last_race.get("last_3f", "")
    margin = last_race.get("margin", "")
    running_style = last_race.get("running_style", "")
    pace = last_race.get("race_pace", "")
    popularity = last_race.get("popularity", 0)
    odds = last_race.get("odds", 0)

    # 着順評価
    if finish == 1:
        finish_eval = "勝利"
    elif finish <= 3:
        finish_eval = "好走"
    elif finish <= 5:
        finish_eval = "掲示板"
    else:
        finish_eval = "凡走"

    # 上がり評価
    last_3f_eval = _evaluate_last_3f(last_3f, finish)

    # 人気との比較
    if popularity and finish:
        if finish < popularity:
            pop_compare = "人気以上"
        elif finish == popularity:
            pop_compare = "人気通り"
        else:
            pop_compare = "人気以下"
    else:
        pop_compare = "不明"

    return {
        "race_name": last_race.get("race_name", ""),
        "race_date": last_race.get("race_date", ""),
        "venue": last_race.get("venue", ""),
        "distance": last_race.get("distance", 0),
        "track_type": last_race.get("track_type", ""),
        "track_condition": last_race.get("track_condition", ""),
        "finish_position": finish,
        "finish_evaluation": finish_eval,
        "total_runners": last_race.get("total_runners", 0),
        "time": time,
        "margin": margin,
        "last_3f": last_3f,
        "last_3f_evaluation": last_3f_eval,
        "running_style": running_style,
        "race_pace": pace,
        "popularity": popularity,
        "odds": odds,
        "vs_popularity": pop_compare,
    }


def _evaluate_last_3f(last_3f: str, finish: int) -> str:
    """上がり3ハロンを評価する."""
    if not last_3f:
        return "不明"

    try:
        time = float(last_3f)
        if time < 33.5:
            return "最速級"
        elif time < 34.0:
            return "速い"
        elif time < 35.0:
            return "標準"
        else:
            return "遅い"
    except ValueError:
        return "不明"


def _analyze_changes(last_race: dict, current_race: dict) -> dict:
    """前走からの変化点を分析する."""
    changes = []

    # 距離変化
    last_distance = last_race.get("distance", 0)
    current_distance = current_race.get("distance", 0)
    distance_diff = current_distance - last_distance

    if distance_diff > 200:
        distance_change = "延長"
        changes.append(f"距離{distance_diff}m延長")
    elif distance_diff < -200:
        distance_change = "短縮"
        changes.append(f"距離{abs(distance_diff)}m短縮")
    else:
        distance_change = "同程度"

    # コース変化
    last_track = last_race.get("track_type", "")
    current_track = current_race.get("track_type", "")
    if last_track != current_track and last_track and current_track:
        track_change = f"{last_track}→{current_track}"
        changes.append(track_change)
    else:
        track_change = "同コース"

    # 競馬場変化
    last_venue = last_race.get("venue", "")
    current_venue = current_race.get("venue", "")
    if last_venue != current_venue and last_venue and current_venue:
        venue_change = f"{last_venue}→{current_venue}"
        changes.append(venue_change)
    else:
        venue_change = "同競馬場"

    # クラス変化
    last_class = last_race.get("grade_class", "")
    current_class = current_race.get("grade_class", "")
    class_change = _compare_class(last_class, current_class)
    if class_change != "同格":
        changes.append(class_change)

    return {
        "distance_diff": distance_diff,
        "distance_change": distance_change,
        "track_change": track_change,
        "venue_change": venue_change,
        "class_change": class_change,
        "summary": "、".join(changes) if changes else "大きな変化なし",
    }


def _compare_class(last_class: str, current_class: str) -> str:
    """クラス比較を行う."""
    class_order = ["新馬", "未勝利", "1勝", "2勝", "3勝", "OP", "L", "G3", "G2", "G1"]

    try:
        last_idx = class_order.index(last_class) if last_class in class_order else -1
        current_idx = class_order.index(current_class) if current_class in class_order else -1
    except ValueError:
        return "不明"

    if last_idx < 0 or current_idx < 0:
        return "不明"
    elif current_idx > last_idx:
        return "格上げ"
    elif current_idx < last_idx:
        return "格下げ"
    else:
        return "同格"


def _evaluate_last_race(last_race: dict, performances: list[dict]) -> dict:
    """前走成績を総合評価する."""
    finish = last_race.get("finish_position", 0)
    last_3f_eval = _evaluate_last_3f(last_race.get("last_3f", ""), finish)

    # 直近5走の平均着順と比較
    recent_finishes = [
        p.get("finish_position", 0)
        for p in performances
        if p.get("finish_position", 0) > 0
    ]

    if recent_finishes:
        avg_finish = sum(recent_finishes) / len(recent_finishes)
        if finish < avg_finish - 1:
            trend = "上昇"
        elif finish > avg_finish + 1:
            trend = "下降"
        else:
            trend = "安定"
    else:
        avg_finish = 0
        trend = "不明"

    # 総合評価
    if finish == 1:
        rating = "A"
        comment = "前走勝利で勢いあり"
    elif finish <= 3 and last_3f_eval in ["最速級", "速い"]:
        rating = "A"
        comment = "前走好走、上がり優秀"
    elif finish <= 3:
        rating = "B+"
        comment = "前走好走"
    elif finish <= 5:
        rating = "B"
        comment = "前走掲示板確保"
    else:
        if last_3f_eval in ["最速級", "速い"]:
            rating = "B-"
            comment = "着順は悪いが上がり良好、巻き返し可能性あり"
        else:
            rating = "C"
            comment = "前走凡走"

    return {
        "rating": rating,
        "trend": trend,
        "avg_recent_finish": round(avg_finish, 1),
        "comment": comment,
    }


def _assess_impact(last_race_analysis: dict, changes: dict, evaluation: dict) -> dict:
    """今回への影響を判断する."""
    rating = evaluation.get("rating", "C")
    class_change = changes.get("class_change", "同格")
    distance_change = changes.get("distance_change", "同程度")

    factors = []
    positive = []
    negative = []

    # 前走成績の影響
    if rating in ["A", "B+"]:
        positive.append("前走好走で勢いあり")
    elif rating == "C":
        negative.append("前走凡走で流れ悪い")

    # クラス変化の影響
    if class_change == "格下げ":
        positive.append("クラス下げで有利")
    elif class_change == "格上げ":
        negative.append("クラス上げで壁がある可能性")

    # 距離変化の影響
    if distance_change in ["延長", "短縮"]:
        factors.append(f"距離{distance_change}の適性がカギ")

    # 総合判定
    if len(positive) > len(negative):
        overall = "プラス材料多い"
        confidence = "高"
    elif len(negative) > len(positive):
        overall = "マイナス材料あり"
        confidence = "低"
    else:
        overall = "五分五分"
        confidence = "中"

    return {
        "overall": overall,
        "confidence": confidence,
        "positive_factors": positive,
        "negative_factors": negative,
        "key_factors": factors,
    }


def _generate_overall_comment(
    horse_name: str,
    last_race_analysis: dict,
    changes: dict,
    evaluation: dict,
    impact: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # 前走結果
    race_name = last_race_analysis.get("race_name", "前走")
    finish = last_race_analysis.get("finish_position", 0)
    parts.append(f"{horse_name}は{race_name}{finish}着")

    # 上がり評価
    last_3f_eval = last_race_analysis.get("last_3f_evaluation", "")
    if last_3f_eval in ["最速級", "速い"]:
        parts.append(f"上がり{last_3f_eval}")

    # 変化点
    changes_summary = changes.get("summary", "")
    if changes_summary and changes_summary != "大きな変化なし":
        parts.append(f"今回は{changes_summary}")

    # 影響判断
    overall = impact.get("overall", "")
    if overall:
        parts.append(overall)

    return "。".join(parts) + "。"
