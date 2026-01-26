"""タイム分析ツール.

走破タイムを分析し、馬の能力を評価する。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# 距離別基準タイム（良馬場、秒）
STANDARD_TIMES = {
    1000: 57.0,
    1200: 69.0,
    1400: 82.0,
    1600: 95.0,
    1800: 108.0,
    2000: 121.0,
    2200: 134.0,
    2400: 147.0,
    2600: 160.0,
    3000: 186.0,
    3200: 199.0,
    3600: 225.0,
}


@tool
def analyze_time_performance(
    horse_id: str,
    horse_name: str,
    race_id: str | None = None,
) -> dict:
    """馬の走破タイムを分析し、能力を評価する。

    過去の走破タイムを分析し、基準タイムとの比較、
    上がりタイムの傾向、タイム的な能力を評価する。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        race_id: 今回のレースID（オプション、条件比較用）

    Returns:
        タイム分析結果（ベストタイム、上がり分析、能力評価）
    """
    try:
        # 今回のレース情報取得（指定時）
        current_race = None
        if race_id:
            current_race = _get_race_info(race_id)
            if "error" in current_race:
                current_race = None

        # 馬の過去成績取得
        performances = _get_performances(horse_id)
        if not performances:
            return {
                "warning": "過去成績データが見つかりませんでした",
                "horse_name": horse_name,
            }

        # ベストタイム分析
        best_times = _analyze_best_times(performances)

        # 上がりタイム分析
        last_3f_analysis = _analyze_last_3f(performances)

        # スピード指数（簡易版）
        speed_rating = _calculate_speed_rating(performances)

        # 条件別タイム分析
        condition_times = _analyze_condition_times(performances)

        # 今回のレースとの比較（指定時）
        race_comparison = None
        if current_race:
            race_comparison = _compare_with_race(best_times, current_race)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            horse_name, best_times, last_3f_analysis, speed_rating, race_comparison
        )

        return {
            "horse_name": horse_name,
            "best_times": best_times,
            "last_3f_analysis": last_3f_analysis,
            "speed_rating": speed_rating,
            "condition_times": condition_times,
            "race_comparison": race_comparison,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze time performance: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze time performance: {e}")
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


def _parse_time(time_str: str) -> float | None:
    """タイム文字列を秒数に変換する."""
    if not time_str:
        return None

    try:
        # "1:33.5" or "33.5" format
        if ":" in time_str:
            parts = time_str.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return None


def _format_time(seconds: float) -> str:
    """秒数をタイム文字列に変換する."""
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes}:{secs:05.2f}"
    else:
        return f"{secs:.1f}"


def _analyze_best_times(performances: list[dict]) -> dict:
    """ベストタイムを分析する."""
    times_by_distance = {}

    for perf in performances:
        distance = perf.get("distance", 0)
        time_str = perf.get("time", "")
        condition = perf.get("track_condition", "良")

        if distance <= 0 or not time_str:
            continue

        seconds = _parse_time(time_str)
        if seconds is None:
            continue

        if distance not in times_by_distance:
            times_by_distance[distance] = []

        times_by_distance[distance].append({
            "time": time_str,
            "seconds": seconds,
            "condition": condition,
            "race_name": perf.get("race_name", ""),
            "race_date": perf.get("race_date", ""),
        })

    # 距離別ベストタイム
    best_times = {}
    for distance, times in times_by_distance.items():
        if times:
            best = min(times, key=lambda x: x["seconds"])
            best_times[distance] = {
                "time": best["time"],
                "seconds": best["seconds"],
                "condition": best["condition"],
                "race_name": best["race_name"],
                "race_date": best["race_date"],
                "standard_diff": _compare_to_standard(distance, best["seconds"], best["condition"]),
            }

    # 全体ベスト
    all_races = [t for times in times_by_distance.values() for t in times]
    overall_best = None
    if all_races:
        # スピード換算で比較
        for t in all_races:
            t["speed"] = t.get("seconds", 999) / (t.get("distance", 1000) or 1000)
        best = min(all_races, key=lambda x: x.get("speed", 999))
        overall_best = {
            "time": best["time"],
            "distance": next((d for d, ts in times_by_distance.items() if best in ts), 0),
            "race_name": best.get("race_name", ""),
        }

    return {
        "by_distance": best_times,
        "overall_best": overall_best,
    }


def _compare_to_standard(distance: int, seconds: float, condition: str) -> dict:
    """基準タイムと比較する."""
    # 最も近い基準距離を取得
    standard_distances = sorted(STANDARD_TIMES.keys())
    closest_distance = min(standard_distances, key=lambda x: abs(x - distance))

    # 距離差を補正
    base_time = STANDARD_TIMES[closest_distance]
    distance_diff = distance - closest_distance
    time_per_100m = base_time / closest_distance * 100
    adjusted_standard = base_time + (distance_diff / 100) * (time_per_100m / closest_distance * 100)

    # 馬場補正
    condition_adjustment = {
        "良": 0.0,
        "稍": 0.5,
        "重": 1.5,
        "不": 3.0,
    }
    adjusted_standard += condition_adjustment.get(condition, 0.0)

    diff = seconds - adjusted_standard

    if diff < -2.0:
        evaluation = "非常に速い"
    elif diff < -1.0:
        evaluation = "速い"
    elif diff < 0.5:
        evaluation = "標準"
    elif diff < 2.0:
        evaluation = "やや遅い"
    else:
        evaluation = "遅い"

    return {
        "standard_time": round(adjusted_standard, 1),
        "diff": round(diff, 1),
        "evaluation": evaluation,
    }


def _analyze_last_3f(performances: list[dict]) -> dict:
    """上がり3ハロンを分析する."""
    last_3fs = []

    for perf in performances:
        last_3f = perf.get("last_3f", "")
        if last_3f:
            try:
                seconds = float(last_3f)
                finish = perf.get("finish_position", 0)
                last_3fs.append({
                    "time": seconds,
                    "finish": finish,
                    "race_name": perf.get("race_name", ""),
                })
            except ValueError:
                continue

    if not last_3fs:
        return {
            "best": None,
            "average": None,
            "trend": "不明",
            "comment": "データ不足",
        }

    best = min(last_3fs, key=lambda x: x["time"])
    average = sum(x["time"] for x in last_3fs) / len(last_3fs)

    # 最近3走と過去を比較
    recent = last_3fs[:3]
    older = last_3fs[3:]

    if recent and older:
        recent_avg = sum(x["time"] for x in recent) / len(recent)
        older_avg = sum(x["time"] for x in older) / len(older)
        diff = older_avg - recent_avg

        if diff >= 0.5:
            trend = "改善"
        elif diff <= -0.5:
            trend = "悪化"
        else:
            trend = "安定"
    else:
        trend = "データ不足"

    # 上がり評価
    if best["time"] < 33.0:
        speed_class = "最速級"
    elif best["time"] < 34.0:
        speed_class = "速い"
    elif best["time"] < 35.0:
        speed_class = "標準"
    else:
        speed_class = "遅い"

    return {
        "best": {
            "time": best["time"],
            "race_name": best["race_name"],
        },
        "average": round(average, 1),
        "trend": trend,
        "speed_class": speed_class,
        "comment": f"ベスト上がり{best['time']}秒（{speed_class}）",
    }


def _calculate_speed_rating(performances: list[dict]) -> dict:
    """スピード指数を計算する（簡易版）."""
    ratings = []

    for perf in performances:
        distance = perf.get("distance", 0)
        time_str = perf.get("time", "")
        condition = perf.get("track_condition", "良")

        if distance <= 0 or not time_str:
            continue

        seconds = _parse_time(time_str)
        if seconds is None:
            continue

        # 簡易スピード指数: (基準タイム - 実タイム) * 係数 + 基準値
        closest = min(STANDARD_TIMES.keys(), key=lambda x: abs(x - distance))
        base = STANDARD_TIMES[closest]

        # 距離補正
        distance_factor = distance / closest
        adjusted_base = base * distance_factor

        # 馬場補正
        condition_adjustment = {"良": 0.0, "稍": 0.5, "重": 1.5, "不": 3.0}
        adjusted_base += condition_adjustment.get(condition, 0.0)

        diff = adjusted_base - seconds
        rating = 80 + diff * 2  # 基準80、1秒差で2ポイント

        ratings.append({
            "rating": round(rating, 1),
            "race_name": perf.get("race_name", ""),
            "distance": distance,
        })

    if not ratings:
        return {
            "best": None,
            "average": None,
            "comment": "データ不足",
        }

    best = max(ratings, key=lambda x: x["rating"])
    average = sum(x["rating"] for x in ratings) / len(ratings)

    # 評価
    if best["rating"] >= 90:
        evaluation = "A"
    elif best["rating"] >= 85:
        evaluation = "B+"
    elif best["rating"] >= 80:
        evaluation = "B"
    else:
        evaluation = "C"

    return {
        "best": best,
        "average": round(average, 1),
        "evaluation": evaluation,
        "comment": f"最高指数{best['rating']}（{evaluation}）",
    }


def _analyze_condition_times(performances: list[dict]) -> dict:
    """条件別タイムを分析する."""
    condition_groups = {
        "良": [],
        "稍": [],
        "重": [],
        "不": [],
    }

    for perf in performances:
        condition = perf.get("track_condition", "良")
        time_str = perf.get("time", "")

        if not time_str:
            continue

        seconds = _parse_time(time_str)
        if seconds is None:
            continue

        # 条件を正規化
        if "不" in condition:
            condition = "不"
        elif "重" in condition:
            condition = "重"
        elif "稍" in condition:
            condition = "稍"
        else:
            condition = "良"

        if condition in condition_groups:
            condition_groups[condition].append(seconds)

    result = {}
    for cond, times in condition_groups.items():
        if times:
            result[cond] = {
                "races": len(times),
                "average": round(sum(times) / len(times), 1),
                "best": round(min(times), 1),
            }
        else:
            result[cond] = {
                "races": 0,
                "average": None,
                "best": None,
            }

    return result


def _compare_with_race(best_times: dict, race_info: dict) -> dict:
    """今回のレースとベストタイムを比較する."""
    distance = race_info.get("distance", 0)

    if distance <= 0:
        return {
            "applicable": False,
            "comment": "距離情報なし",
        }

    by_distance = best_times.get("by_distance", {})

    # 同距離のベストタイム
    if distance in by_distance:
        best = by_distance[distance]
        return {
            "applicable": True,
            "distance": distance,
            "best_time": best["time"],
            "standard_diff": best["standard_diff"],
            "comment": f"{distance}mベスト{best['time']}、基準{best['standard_diff']['evaluation']}",
        }

    # 近い距離のベストタイム
    closest = min(by_distance.keys(), key=lambda x: abs(x - distance)) if by_distance else None
    if closest:
        best = by_distance[closest]
        return {
            "applicable": True,
            "distance": distance,
            "closest_distance": closest,
            "closest_time": best["time"],
            "comment": f"同距離実績なし、{closest}mでは{best['time']}",
        }

    return {
        "applicable": False,
        "comment": "比較可能なタイムなし",
    }


def _generate_overall_comment(
    horse_name: str,
    best_times: dict,
    last_3f_analysis: dict,
    speed_rating: dict,
    race_comparison: dict | None,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # スピード評価
    eval = speed_rating.get("evaluation", "")
    if eval == "A":
        parts.append(f"{horse_name}はタイム優秀")
    elif eval in ["C"]:
        parts.append(f"{horse_name}はタイムで劣る")

    # 上がり評価
    speed_class = last_3f_analysis.get("speed_class", "")
    if speed_class == "最速級":
        parts.append("上がり最速級")
    elif speed_class == "速い":
        parts.append("上がり速い")

    # 今回との比較
    if race_comparison and race_comparison.get("applicable"):
        std_eval = race_comparison.get("standard_diff", {}).get("evaluation", "")
        if std_eval in ["非常に速い", "速い"]:
            parts.append("この距離でタイム優秀")

    return "。".join(parts) + "。" if parts else "タイム面は普通。"
