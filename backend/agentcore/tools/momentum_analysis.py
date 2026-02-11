"""連勝馬・勢い分析ツール.

馬の勢い・連勝状況を分析し、上昇傾向かどうかを判断する。
"""

import logging

import requests
from strands import tool

from .jravan_client import cached_get, get_api_url

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30


@tool
def analyze_momentum(
    horse_id: str,
    horse_name: str,
) -> dict:
    """馬の勢い・連勝状況を分析する。

    直近の成績から馬の勢いを分析し、
    上昇傾向・下降傾向・安定傾向を判断する。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）

    Returns:
        勢い分析結果（連勝状況、トレンド、勢い評価）
    """
    try:
        # 馬の過去成績取得
        performances = _get_performances(horse_id)
        if not performances:
            return {
                "warning": "過去成績データが見つかりませんでした",
                "horse_name": horse_name,
            }

        # 連勝分析
        winning_streak = _analyze_winning_streak(performances)

        # 連対分析
        placing_streak = _analyze_placing_streak(performances)

        # トレンド分析
        trend = _analyze_trend(performances)

        # 勢い評価
        momentum = _evaluate_momentum(winning_streak, placing_streak, trend)

        # 上がり傾向分析
        finishing_trend = _analyze_finishing_trend(performances)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            horse_name, winning_streak, placing_streak, trend, momentum, finishing_trend
        )

        return {
            "horse_name": horse_name,
            "winning_streak": winning_streak,
            "placing_streak": placing_streak,
            "trend": trend,
            "momentum": momentum,
            "finishing_trend": finishing_trend,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze momentum: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze momentum: {e}")
        return {"error": str(e)}


def _get_performances(horse_id: str) -> list[dict]:
    """過去成績を取得する."""
    try:
        response = cached_get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": 10},
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("performances", data) if isinstance(data, dict) else data
        return []
    except requests.RequestException as e:
        logger.error(f"Failed to get performances for horse {horse_id}: {e}")
        return []


def _analyze_winning_streak(performances: list[dict]) -> dict:
    """連勝状況を分析する."""
    if not performances:
        return {
            "current_streak": 0,
            "is_on_streak": False,
            "max_streak": 0,
            "comment": "データ不足",
        }

    # 現在の連勝
    current_streak = 0
    for perf in performances:
        if perf.get("finish_position") == 1:
            current_streak += 1
        else:
            break

    # 最大連勝
    max_streak = 0
    temp_streak = 0
    for perf in performances:
        if perf.get("finish_position") == 1:
            temp_streak += 1
            max_streak = max(max_streak, temp_streak)
        else:
            temp_streak = 0

    is_on_streak = current_streak >= 2

    if current_streak >= 3:
        comment = f"{current_streak}連勝中、絶好調"
    elif current_streak == 2:
        comment = "2連勝中、勢いあり"
    elif current_streak == 1:
        comment = "前走勝利"
    else:
        comment = "連勝中ではない"

    return {
        "current_streak": current_streak,
        "is_on_streak": is_on_streak,
        "max_streak": max_streak,
        "comment": comment,
    }


def _analyze_placing_streak(performances: list[dict]) -> dict:
    """連対・連続好走状況を分析する."""
    if not performances:
        return {
            "current_placing_streak": 0,
            "current_top5_streak": 0,
            "comment": "データ不足",
        }

    # 連続連対（3着以内）
    placing_streak = 0
    for perf in performances:
        finish = perf.get("finish_position", 99)
        if 1 <= finish <= 3:
            placing_streak += 1
        else:
            break

    # 連続掲示板（5着以内）
    top5_streak = 0
    for perf in performances:
        finish = perf.get("finish_position", 99)
        if 1 <= finish <= 5:
            top5_streak += 1
        else:
            break

    if placing_streak >= 5:
        comment = f"{placing_streak}戦連続好走、絶好調"
    elif placing_streak >= 3:
        comment = f"{placing_streak}戦連続3着以内"
    elif placing_streak >= 1:
        comment = f"直近{placing_streak}戦好走"
    elif top5_streak >= 3:
        comment = f"{top5_streak}戦連続掲示板"
    else:
        comment = "好走続いていない"

    return {
        "current_placing_streak": placing_streak,
        "current_top5_streak": top5_streak,
        "comment": comment,
    }


def _analyze_trend(performances: list[dict]) -> dict:
    """トレンドを分析する."""
    if len(performances) < 3:
        return {
            "direction": "不明",
            "strength": "不明",
            "recent_avg": 0.0,
            "older_avg": 0.0,
            "comment": "データ不足",
        }

    # 直近3走と過去3走を比較
    recent = performances[:3]
    older = performances[3:6] if len(performances) >= 6 else performances[3:]

    recent_finishes = [p.get("finish_position", 0) for p in recent if p.get("finish_position", 0) > 0]
    older_finishes = [p.get("finish_position", 0) for p in older if p.get("finish_position", 0) > 0]

    if not recent_finishes:
        return {
            "direction": "不明",
            "strength": "不明",
            "recent_avg": 0.0,
            "older_avg": 0.0,
            "comment": "着順データ不足",
        }

    recent_avg = sum(recent_finishes) / len(recent_finishes)

    if older_finishes:
        older_avg = sum(older_finishes) / len(older_finishes)
        diff = older_avg - recent_avg  # プラスなら上昇傾向
    else:
        older_avg = 0.0
        diff = 0.0

    if diff >= 2.0:
        direction = "急上昇"
        strength = "強"
    elif diff >= 1.0:
        direction = "上昇"
        strength = "中"
    elif diff >= 0.3:
        direction = "やや上昇"
        strength = "弱"
    elif diff <= -2.0:
        direction = "急下降"
        strength = "強"
    elif diff <= -1.0:
        direction = "下降"
        strength = "中"
    elif diff <= -0.3:
        direction = "やや下降"
        strength = "弱"
    else:
        direction = "横ばい"
        strength = "中"

    comment = f"直近平均{round(recent_avg, 1)}着、{direction}傾向"

    return {
        "direction": direction,
        "strength": strength,
        "recent_avg": round(recent_avg, 1),
        "older_avg": round(older_avg, 1),
        "diff": round(diff, 1),
        "comment": comment,
    }


def _evaluate_momentum(
    winning_streak: dict,
    placing_streak: dict,
    trend: dict,
) -> dict:
    """勢いを総合評価する."""
    score = 0

    # 連勝評価
    current_wins = winning_streak.get("current_streak", 0)
    if current_wins >= 3:
        score += 30
    elif current_wins >= 2:
        score += 20
    elif current_wins >= 1:
        score += 10

    # 連対評価
    placing = placing_streak.get("current_placing_streak", 0)
    if placing >= 5:
        score += 25
    elif placing >= 3:
        score += 15
    elif placing >= 1:
        score += 5

    # トレンド評価
    direction = trend.get("direction", "")
    if direction == "急上昇":
        score += 25
    elif direction == "上昇":
        score += 15
    elif direction == "やや上昇":
        score += 5
    elif direction == "急下降":
        score -= 20
    elif direction == "下降":
        score -= 10

    # 評価
    if score >= 50:
        rating = "A"
        description = "絶好調"
    elif score >= 30:
        rating = "B+"
        description = "好調"
    elif score >= 15:
        rating = "B"
        description = "普通"
    elif score >= 0:
        rating = "C+"
        description = "やや不調"
    else:
        rating = "C"
        description = "不調"

    return {
        "rating": rating,
        "score": score,
        "description": description,
    }


def _analyze_finishing_trend(performances: list[dict]) -> dict:
    """上がりタイムのトレンドを分析する."""
    last_3fs = []
    for perf in performances[:5]:
        last_3f = perf.get("last_3f")
        if last_3f:
            try:
                last_3fs.append(float(last_3f))
            except ValueError:
                continue

    if len(last_3fs) < 2:
        return {
            "trend": "不明",
            "recent_avg": None,
            "comment": "データ不足",
        }

    recent_avg = sum(last_3fs[:2]) / 2 if len(last_3fs) >= 2 else last_3fs[0]
    older_avg = sum(last_3fs[2:]) / len(last_3fs[2:]) if len(last_3fs) > 2 else recent_avg

    diff = older_avg - recent_avg  # プラスなら上がり改善

    if diff >= 0.5:
        trend = "改善"
        comment = "上がりタイム向上中"
    elif diff >= 0.2:
        trend = "やや改善"
        comment = "上がりやや向上"
    elif diff <= -0.5:
        trend = "悪化"
        comment = "上がりタイム悪化傾向"
    else:
        trend = "安定"
        comment = "上がり安定"

    return {
        "trend": trend,
        "recent_avg": round(recent_avg, 1),
        "older_avg": round(older_avg, 1),
        "comment": comment,
    }


def _generate_overall_comment(
    horse_name: str,
    winning_streak: dict,
    placing_streak: dict,
    trend: dict,
    momentum: dict,
    finishing_trend: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # 連勝状況
    current_wins = winning_streak.get("current_streak", 0)
    if current_wins >= 2:
        parts.append(f"{horse_name}は{current_wins}連勝中")
    elif current_wins == 1:
        parts.append(f"{horse_name}は前走勝利")

    # 連対状況
    placing = placing_streak.get("current_placing_streak", 0)
    if placing >= 3 and current_wins < 2:
        parts.append(f"{placing}戦連続好走")

    # 勢い評価
    rating = momentum.get("rating", "")
    description = momentum.get("description", "")
    if rating == "A":
        parts.append(description)
    elif rating == "C":
        parts.append(description)

    # トレンド
    direction = trend.get("direction", "")
    if direction in ["急上昇", "上昇"]:
        parts.append("調子上向き")
    elif direction in ["急下降", "下降"]:
        parts.append("調子下降気味")

    return "。".join(parts) + "。" if parts else "勢いは普通。"
