"""距離変更影響分析ツール.

距離変更が出走馬に与える影響を分析する。
"""

import logging

import requests
from strands import tool

from .jravan_client import cached_get, get_api_url

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# 距離カテゴリ
DISTANCE_CATEGORIES = {
    "短距離": (1000, 1400),
    "マイル": (1400, 1800),
    "中距離": (1800, 2200),
    "中長距離": (2200, 2600),
    "長距離": (2600, 4000),
}


@tool
def analyze_distance_change(
    race_id: str,
    horse_id: str,
    horse_name: str,
) -> dict:
    """距離変更が馬に与える影響を分析する。

    前走からの距離変更を分析し、この馬の距離適性から
    今回の距離が合っているかを判断する。

    Args:
        race_id: 対象レースID
        horse_id: 馬コード
        horse_name: 馬名（表示用）

    Returns:
        距離変更分析結果（距離別成績、変更影響、適性評価）
    """
    try:
        # レース情報取得
        race_info = _get_race_info(race_id)
        if "error" in race_info:
            return race_info

        current_distance = race_info.get("distance", 0)

        # 馬の過去成績取得
        performances = _get_performances(horse_id)
        if not performances:
            return {
                "warning": "過去成績データが見つかりませんでした",
                "horse_name": horse_name,
            }

        # 距離別成績を分析
        distance_stats = _analyze_distance_stats(performances)

        # 距離変更分析
        distance_change = _analyze_distance_change(performances, current_distance)

        # 距離適性評価
        aptitude = _evaluate_distance_aptitude(
            distance_stats, current_distance, distance_change
        )

        # ベスト距離分析
        best_distance = _analyze_best_distance(distance_stats, performances)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            horse_name, current_distance, distance_stats, distance_change, aptitude, best_distance
        )

        return {
            "horse_name": horse_name,
            "current_distance": current_distance,
            "distance_stats": distance_stats,
            "distance_change": distance_change,
            "aptitude": aptitude,
            "best_distance": best_distance,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze distance change: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze distance change: {e}")
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


def _get_performances(horse_id: str) -> list[dict]:
    """過去成績を取得する."""
    try:
        response = cached_get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": 20},
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("performances", data) if isinstance(data, dict) else data
        return []
    except requests.RequestException as e:
        logger.error(f"Failed to get performances for horse {horse_id}: {e}")
        return []


def _get_distance_category(distance: int) -> str:
    """距離カテゴリを取得する."""
    for category, (min_d, max_d) in DISTANCE_CATEGORIES.items():
        if min_d <= distance < max_d:
            return category
    return "不明"


def _analyze_distance_stats(performances: list[dict]) -> dict:
    """距離別成績を分析する."""
    stats = {cat: {"runs": 0, "wins": 0, "places": 0, "finishes": []}
             for cat in DISTANCE_CATEGORIES.keys()}

    for perf in performances:
        distance = perf.get("distance", 0)
        if distance <= 0:
            continue

        category = _get_distance_category(distance)
        if category not in stats:
            continue

        finish = perf.get("finish_position", 0)
        if finish <= 0:
            continue

        stats[category]["runs"] += 1
        stats[category]["finishes"].append(finish)
        if finish == 1:
            stats[category]["wins"] += 1
        if finish <= 3:
            stats[category]["places"] += 1

    # 成績フォーマット
    result = {}
    for cat, s in stats.items():
        runs = s["runs"]
        if runs > 0:
            win_rate = round((s["wins"] / runs) * 100, 1)
            place_rate = round((s["places"] / runs) * 100, 1)
            avg_finish = round(sum(s["finishes"]) / runs, 1)
        else:
            win_rate = 0.0
            place_rate = 0.0
            avg_finish = 0.0

        result[cat] = {
            "runs": runs,
            "wins": s["wins"],
            "places": s["places"],
            "record": f"{s['wins']}-{s['places'] - s['wins']}-{runs - s['places']}",
            "win_rate": win_rate,
            "place_rate": place_rate,
            "avg_finish": avg_finish,
        }

    return result


def _analyze_distance_change(performances: list[dict], current_distance: int) -> dict:
    """距離変更を分析する."""
    if not performances:
        return {
            "change_type": "不明",
            "change_meters": 0,
            "comment": "データ不足",
        }

    last_distance = performances[0].get("distance", 0)
    if last_distance <= 0:
        return {
            "change_type": "不明",
            "change_meters": 0,
            "comment": "前走距離不明",
        }

    change = current_distance - last_distance

    if change > 400:
        change_type = "大幅延長"
        comment = f"{change}m延長は大きな変化"
    elif change > 200:
        change_type = "延長"
        comment = f"{change}m延長"
    elif change > 0:
        change_type = "微増"
        comment = f"{change}m延長、影響は限定的"
    elif change < -400:
        change_type = "大幅短縮"
        comment = f"{abs(change)}m短縮は大きな変化"
    elif change < -200:
        change_type = "短縮"
        comment = f"{abs(change)}m短縮"
    elif change < 0:
        change_type = "微減"
        comment = f"{abs(change)}m短縮、影響は限定的"
    else:
        change_type = "同距離"
        comment = "前走と同距離"

    # カテゴリ変化
    last_cat = _get_distance_category(last_distance)
    current_cat = _get_distance_category(current_distance)
    category_changed = last_cat != current_cat

    return {
        "change_type": change_type,
        "change_meters": change,
        "last_distance": last_distance,
        "current_distance": current_distance,
        "last_category": last_cat,
        "current_category": current_cat,
        "category_changed": category_changed,
        "comment": comment,
    }


def _evaluate_distance_aptitude(
    distance_stats: dict,
    current_distance: int,
    distance_change: dict,
) -> dict:
    """距離適性を評価する."""
    current_cat = _get_distance_category(current_distance)
    current_stats = distance_stats.get(current_cat, {})

    runs = current_stats.get("runs", 0)
    win_rate = current_stats.get("win_rate", 0.0)
    place_rate = current_stats.get("place_rate", 0.0)

    if runs >= 3:
        if win_rate >= 25:
            rating = "A"
            comment = f"{current_cat}で勝利実績あり、適性高い"
        elif place_rate >= 50:
            rating = "B+"
            comment = f"{current_cat}で好走率高い"
        elif place_rate >= 30:
            rating = "B"
            comment = f"{current_cat}で安定"
        else:
            rating = "C"
            comment = f"{current_cat}は苦手傾向"
    elif runs > 0:
        if win_rate > 0:
            rating = "B+"
            comment = f"{current_cat}経験あり、勝利実績"
        else:
            rating = "B"
            comment = f"{current_cat}経験あり"
    else:
        # 未経験
        if distance_change.get("category_changed"):
            rating = "C+"
            comment = f"{current_cat}は初挑戦、未知数"
        else:
            rating = "B"
            comment = "距離経験なしだが同カテゴリ"

    # 距離変更の影響を加味
    change_type = distance_change.get("change_type", "")
    if change_type in ["大幅延長", "大幅短縮"]:
        if rating == "A":
            rating = "B+"
        elif rating == "B+":
            rating = "B"
        comment += f"（{change_type}に注意）"

    return {
        "rating": rating,
        "category": current_cat,
        "runs_in_category": runs,
        "win_rate": win_rate,
        "place_rate": place_rate,
        "comment": comment,
    }


def _analyze_best_distance(distance_stats: dict, performances: list[dict]) -> dict:
    """ベスト距離を分析する."""
    # 最も成績の良いカテゴリ
    best_cat = None
    best_rate = -1.0

    for cat, stats in distance_stats.items():
        if stats.get("runs", 0) >= 2:
            rate = stats.get("place_rate", 0.0)
            if rate > best_rate:
                best_rate = rate
                best_cat = cat

    # 具体的なベスト距離（勝利距離の最頻値）
    win_distances = [
        p.get("distance", 0)
        for p in performances
        if p.get("finish_position") == 1 and p.get("distance", 0) > 0
    ]

    if win_distances:
        # 最頻値または中央値
        best_distance = max(set(win_distances), key=win_distances.count)
    else:
        # 勝利がなければ好走距離
        place_distances = [
            p.get("distance", 0)
            for p in performances
            if p.get("finish_position", 99) <= 3 and p.get("distance", 0) > 0
        ]
        if place_distances:
            best_distance = max(set(place_distances), key=place_distances.count)
        else:
            best_distance = None

    return {
        "best_category": best_cat,
        "best_category_place_rate": best_rate,
        "best_distance": best_distance,
        "comment": f"ベストは{best_cat}（{best_distance}m前後）" if best_cat and best_distance else "ベスト距離は不明",
    }


def _generate_overall_comment(
    horse_name: str,
    current_distance: int,
    distance_stats: dict,
    distance_change: dict,
    aptitude: dict,
    best_distance: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # 距離変更
    change_type = distance_change.get("change_type", "")
    change_meters = distance_change.get("change_meters", 0)
    if change_type in ["大幅延長", "大幅短縮"]:
        parts.append(f"{horse_name}は{abs(change_meters)}m{change_type.replace('大幅', '')}")
    elif change_type in ["延長", "短縮"]:
        parts.append(f"{horse_name}は{abs(change_meters)}m{change_type}")

    # 距離適性
    rating = aptitude.get("rating", "")
    category = aptitude.get("category", "")
    if rating == "A":
        parts.append(f"{category}が得意")
    elif rating in ["C", "C+"]:
        parts.append(f"{category}は未知数or苦手")

    # ベスト距離との比較
    best_dist = best_distance.get("best_distance")
    if best_dist:
        diff = abs(current_distance - best_dist)
        if diff <= 200:
            parts.append("ベスト距離に近い")
        elif diff >= 400:
            parts.append("ベスト距離から離れる")

    return "。".join(parts) + "。" if parts else "距離適性は普通。"
