"""馬場変化追跡ツール.

レース中の馬場状態の変化を追跡し、影響を分析する。
"""

import logging

import requests
from strands import tool

from .jravan_client import cached_get, get_api_url

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# 馬場状態の重さ順序
CONDITION_WEIGHT = {
    "良": 1,
    "稍": 2,
    "重": 3,
    "不": 4,
}


def _normalize_track_condition(condition: str) -> str:
    """馬場状態を正規化する（稍重→稍、不良→不など）."""
    if not condition:
        return "良"
    if "不" in condition:
        return "不"
    if "重" in condition:
        return "重"
    if "稍" in condition:
        return "稍"
    return "良"


@tool
def track_course_condition_change(
    race_id: str,
) -> dict:
    """馬場状態の変化を追跡し、影響を分析する。

    当日の馬場状態の変化を追跡し、
    レースへの影響を予測する。

    Args:
        race_id: 対象レースID

    Returns:
        馬場変化分析結果（変化履歴、予測、脚質別影響）
    """
    try:
        # レース情報取得
        race_info = _get_race_info(race_id)
        if "error" in race_info:
            return race_info

        venue = race_info.get("venue", "")
        current_condition = race_info.get("track_condition", "良")
        track_type = race_info.get("track_type", "芝")
        distance = race_info.get("distance", 0)

        # 当日の他レース情報から馬場変化を推測
        daily_races = _get_daily_races(race_info.get("race_date", ""), venue)

        # 馬場変化分析
        condition_change = _analyze_condition_change(daily_races, race_info)

        # 脚質別影響予測
        running_style_impact = _predict_running_style_impact(current_condition, condition_change)

        # タイム影響予測
        time_impact = _predict_time_impact(current_condition, track_type, distance)

        # 枠順影響予測
        gate_impact = _predict_gate_impact(current_condition, track_type)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            venue, current_condition, condition_change, running_style_impact, time_impact
        )

        return {
            "venue": venue,
            "track_type": track_type,
            "current_condition": current_condition,
            "condition_change": condition_change,
            "running_style_impact": running_style_impact,
            "time_impact": time_impact,
            "gate_impact": gate_impact,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to track course condition change: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to track course condition change: {e}")
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


def _get_daily_races(race_date: str, venue: str) -> list[dict]:
    """当日の全レース情報を取得する."""
    try:
        # race_dateをYYYYMMDD形式に変換
        if "-" in race_date:
            race_date = race_date.replace("-", "")

        response = cached_get(
            f"{get_api_url()}/races",
            params={"date": race_date, "venue": venue},
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException as e:
        logger.error(f"Failed to get daily races: {e}")
        return []


def _analyze_condition_change(daily_races: list[dict], current_race: dict) -> dict:
    """馬場状態の変化を分析する."""
    if not daily_races:
        return {
            "trend": "不明",
            "history": [],
            "comment": "当日データ不足",
        }

    current_race_number = current_race.get("race_number", 0)
    current_track = current_race.get("track_type", "")

    # 同じコース種別（芝/ダート）のレースをフィルタ
    same_track_races = [
        r for r in daily_races
        if r.get("track_type") == current_track and r.get("race_number", 0) < current_race_number
    ]

    if not same_track_races:
        return {
            "trend": "初戦",
            "history": [],
            "comment": f"本日{current_track}初戦",
        }

    # 馬場状態の履歴（正規化して保存）
    history = []
    for race in sorted(same_track_races, key=lambda x: x.get("race_number", 0)):
        condition = _normalize_track_condition(race.get("track_condition", "良"))
        history.append({
            "race_number": race.get("race_number"),
            "condition": condition,
        })

    # トレンド判定（正規化済みの条件で重みを取得）
    if len(history) >= 2:
        first_weight = CONDITION_WEIGHT.get(history[0]["condition"], 1)
        last_weight = CONDITION_WEIGHT.get(history[-1]["condition"], 1)

        if last_weight > first_weight:
            trend = "悪化傾向"
            comment = "馬場が悪化傾向"
        elif last_weight < first_weight:
            trend = "回復傾向"
            comment = "馬場が回復傾向"
        else:
            trend = "安定"
            comment = "馬場状態安定"
    else:
        trend = "判定中"
        comment = "データ蓄積中"

    return {
        "trend": trend,
        "history": history,
        "races_completed": len(history),
        "comment": comment,
    }


def _predict_running_style_impact(condition: str, condition_change: dict) -> dict:
    """脚質別影響を予測する."""
    # 馬場状態による脚質有利不利
    if condition in ["重", "不"]:
        # 道悪は先行有利
        advantage = {
            "逃げ": "有利",
            "先行": "有利",
            "差し": "不利",
            "追込": "不利",
        }
        comment = "道悪馬場は前残り傾向"
    elif condition == "稍":
        advantage = {
            "逃げ": "やや有利",
            "先行": "やや有利",
            "差し": "普通",
            "追込": "やや不利",
        }
        comment = "稍重は先行有利だが差しも届く"
    else:  # 良
        advantage = {
            "逃げ": "普通",
            "先行": "普通",
            "差し": "普通",
            "追込": "普通",
        }
        comment = "良馬場は脚質の影響小さい"

    # 変化傾向を加味
    trend = condition_change.get("trend", "")
    if trend == "悪化傾向":
        comment += "、さらに悪化の可能性"
    elif trend == "回復傾向":
        comment += "、回復傾向"

    return {
        "advantage": advantage,
        "best_style": "逃げ・先行" if condition in ["重", "不"] else "脚質問わず",
        "comment": comment,
    }


def _predict_time_impact(condition: str, track_type: str, distance: int) -> dict:
    """タイムへの影響を予測する."""
    # 基準タイム補正（良馬場比）
    time_correction = {
        "良": 0.0,
        "稍": 0.5,  # 約0.5秒遅くなる
        "重": 1.5,  # 約1.5秒遅くなる
        "不": 3.0,  # 約3秒遅くなる
    }

    correction = time_correction.get(condition, 0.0)

    # 距離による補正
    if distance >= 2000:
        correction *= 1.2  # 長距離は影響大
    elif distance <= 1400:
        correction *= 0.8  # 短距離は影響小

    if correction >= 2.0:
        impact_level = "大"
        comment = "タイムは大幅に遅くなる予想"
    elif correction >= 1.0:
        impact_level = "中"
        comment = "タイムはやや遅くなる予想"
    elif correction >= 0.3:
        impact_level = "小"
        comment = "タイムへの影響は小さい"
    else:
        impact_level = "なし"
        comment = "タイムへの影響はほぼなし"

    return {
        "expected_time_correction": round(correction, 1),
        "impact_level": impact_level,
        "comment": comment,
    }


def _predict_gate_impact(condition: str, track_type: str) -> dict:
    """枠順への影響を予測する."""
    if condition in ["重", "不"]:
        if track_type == "芝":
            # 芝の道悪は内枠有利（荒れた外を避けられる）
            inner_advantage = "有利"
            outer_advantage = "不利"
            comment = "荒れた外を避けられる内枠有利"
        else:  # ダート
            # ダートの道悪は外枠有利（砂かぶり軽減）
            inner_advantage = "やや不利"
            outer_advantage = "やや有利"
            comment = "ダート道悪は砂かぶり軽減で外枠やや有利"
    else:
        inner_advantage = "普通"
        outer_advantage = "普通"
        comment = "馬場状態による枠順影響は小さい"

    return {
        "inner_gates": inner_advantage,
        "outer_gates": outer_advantage,
        "comment": comment,
    }


def _generate_overall_comment(
    venue: str,
    condition: str,
    condition_change: dict,
    running_style_impact: dict,
    time_impact: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # 現在の馬場状態
    parts.append(f"{venue}は{condition}馬場")

    # 変化傾向
    trend = condition_change.get("trend", "")
    if trend == "悪化傾向":
        parts.append("さらに悪化傾向")
    elif trend == "回復傾向":
        parts.append("回復傾向")

    # 脚質影響
    best_style = running_style_impact.get("best_style", "")
    if "先行" in best_style:
        parts.append("先行有利の展開予想")

    # タイム影響
    impact_level = time_impact.get("impact_level", "")
    if impact_level in ["大", "中"]:
        parts.append("タイムは遅くなる見込み")

    return "。".join(parts) + "。"
