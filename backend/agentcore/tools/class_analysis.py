"""クラス分析ツール.

レースのクラス・格付けを分析し、出走馬のクラス適性を判断する。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# クラス順序（低い→高い）
CLASS_ORDER = ["新馬", "未勝利", "1勝", "2勝", "3勝", "OP", "L", "G3", "G2", "G1"]

# クラス別の勝馬平均オッズ（参考値）
CLASS_AVG_ODDS = {
    "新馬": 4.5,
    "未勝利": 5.0,
    "1勝": 5.5,
    "2勝": 6.0,
    "3勝": 6.5,
    "OP": 7.0,
    "L": 7.5,
    "G3": 8.0,
    "G2": 6.5,
    "G1": 5.5,
}


@tool
def analyze_class_factor(
    race_id: str,
    horse_id: str,
    horse_name: str,
) -> dict:
    """レースクラスと馬のクラス適性を分析する。

    出走馬の過去のクラス別成績を分析し、
    今回のレースクラスへの適性を判断する。

    Args:
        race_id: 対象レースID
        horse_id: 馬コード
        horse_name: 馬名（表示用）

    Returns:
        クラス分析結果（クラス別成績、昇級・降級判定、適性評価）
    """
    try:
        # レース情報取得
        race_info = _get_race_info(race_id)
        if "error" in race_info:
            return race_info

        current_class = race_info.get("grade_class", "")
        if not current_class:
            current_class = race_info.get("grade", "OP")

        # 馬の過去成績取得
        performances = _get_performances(horse_id)
        if not performances:
            return {
                "warning": "過去成績データが見つかりませんでした",
                "horse_name": horse_name,
            }

        # クラス別成績を分析
        class_stats = _analyze_class_stats(performances)

        # 昇級・降級判定
        class_movement = _analyze_class_movement(performances, current_class)

        # クラス適性評価
        aptitude = _evaluate_class_aptitude(class_stats, current_class, class_movement)

        # クラス実績分析
        class_record = _analyze_class_record(performances, current_class)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            horse_name, current_class, class_stats, class_movement, aptitude, class_record
        )

        return {
            "horse_name": horse_name,
            "current_class": current_class,
            "class_stats": class_stats,
            "class_movement": class_movement,
            "aptitude": aptitude,
            "class_record": class_record,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze class factor: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze class factor: {e}")
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


def _analyze_class_stats(performances: list[dict]) -> dict:
    """クラス別成績を分析する."""
    stats = {}

    for perf in performances:
        grade = perf.get("grade_class", "")
        if not grade:
            continue

        if grade not in stats:
            stats[grade] = {"runs": 0, "wins": 0, "places": 0, "finishes": []}

        finish = perf.get("finish_position", 0)
        if finish <= 0:
            continue

        stats[grade]["runs"] += 1
        stats[grade]["finishes"].append(finish)
        if finish == 1:
            stats[grade]["wins"] += 1
        if finish <= 3:
            stats[grade]["places"] += 1

    # 成績フォーマット
    result = {}
    for grade, s in stats.items():
        runs = s["runs"]
        if runs > 0:
            win_rate = round((s["wins"] / runs) * 100, 1)
            place_rate = round((s["places"] / runs) * 100, 1)
            avg_finish = round(sum(s["finishes"]) / runs, 1)
        else:
            win_rate = 0.0
            place_rate = 0.0
            avg_finish = 0.0

        result[grade] = {
            "runs": runs,
            "wins": s["wins"],
            "places": s["places"],
            "record": f"{s['wins']}-{s['places'] - s['wins']}-{runs - s['places']}",
            "win_rate": win_rate,
            "place_rate": place_rate,
            "avg_finish": avg_finish,
        }

    return result


def _analyze_class_movement(performances: list[dict], current_class: str) -> dict:
    """昇級・降級を分析する."""
    if not performances:
        return {
            "movement_type": "不明",
            "steps": 0,
            "comment": "データ不足",
        }

    # 前走クラス
    last_class = performances[0].get("grade_class", "")
    if not last_class:
        return {
            "movement_type": "不明",
            "steps": 0,
            "comment": "前走クラス不明",
        }

    # クラス比較
    try:
        last_idx = CLASS_ORDER.index(last_class) if last_class in CLASS_ORDER else -1
        current_idx = CLASS_ORDER.index(current_class) if current_class in CLASS_ORDER else -1
    except ValueError:
        return {
            "movement_type": "不明",
            "steps": 0,
            "comment": "クラス判定不可",
        }

    if last_idx < 0 or current_idx < 0:
        return {
            "movement_type": "不明",
            "steps": 0,
            "comment": "クラス判定不可",
        }

    steps = current_idx - last_idx

    if steps > 0:
        movement_type = "昇級"
        if steps >= 2:
            comment = f"前走{last_class}から{steps}階級昇級、大きな壁"
        else:
            comment = f"前走{last_class}から昇級初戦"
    elif steps < 0:
        movement_type = "降級"
        comment = f"前走{last_class}から格下げ、有利"
    else:
        movement_type = "同格"
        comment = f"前走と同じ{current_class}クラス"

    return {
        "movement_type": movement_type,
        "last_class": last_class,
        "current_class": current_class,
        "steps": steps,
        "comment": comment,
    }


def _evaluate_class_aptitude(
    class_stats: dict,
    current_class: str,
    class_movement: dict,
) -> dict:
    """クラス適性を評価する."""
    # 現クラスでの実績
    current_stats = class_stats.get(current_class, {})
    current_runs = current_stats.get("runs", 0)
    current_win_rate = current_stats.get("win_rate", 0.0)
    current_place_rate = current_stats.get("place_rate", 0.0)

    # 上位クラスでの実績
    upper_class_record = _get_upper_class_record(class_stats, current_class)

    # 評価
    if current_runs >= 3:
        if current_win_rate >= 20:
            rating = "A"
            comment = f"{current_class}クラスで勝ち星あり、実績十分"
        elif current_place_rate >= 50:
            rating = "B+"
            comment = f"{current_class}クラスで好走率高い"
        elif current_place_rate >= 30:
            rating = "B"
            comment = f"{current_class}クラスで安定"
        else:
            rating = "C"
            comment = f"{current_class}クラスで苦戦"
    elif current_runs > 0:
        if current_win_rate > 0:
            rating = "B+"
            comment = f"{current_class}クラス経験あり、勝利実績"
        else:
            rating = "B"
            comment = f"{current_class}クラス経験あり"
    else:
        # 初挑戦
        movement = class_movement.get("movement_type", "")
        if movement == "昇級":
            if upper_class_record.get("has_record"):
                rating = "B"
                comment = "昇級だが上位クラス経験あり"
            else:
                rating = "C+"
                comment = "昇級初戦、未知数"
        elif movement == "降級":
            rating = "B+"
            comment = "格下げで有利な立場"
        else:
            rating = "B"
            comment = "クラス適性は普通"

    return {
        "rating": rating,
        "runs_in_class": current_runs,
        "win_rate_in_class": current_win_rate,
        "place_rate_in_class": current_place_rate,
        "upper_class_record": upper_class_record,
        "comment": comment,
    }


def _get_upper_class_record(class_stats: dict, current_class: str) -> dict:
    """上位クラスでの実績を取得する."""
    try:
        current_idx = CLASS_ORDER.index(current_class) if current_class in CLASS_ORDER else -1
    except ValueError:
        return {"has_record": False}

    if current_idx < 0:
        return {"has_record": False}

    upper_classes = CLASS_ORDER[current_idx + 1:]
    total_runs = 0
    total_wins = 0
    total_places = 0

    for upper in upper_classes:
        if upper in class_stats:
            stats = class_stats[upper]
            total_runs += stats.get("runs", 0)
            total_wins += stats.get("wins", 0)
            total_places += stats.get("places", 0)

    has_record = total_runs > 0

    return {
        "has_record": has_record,
        "runs": total_runs,
        "wins": total_wins,
        "places": total_places,
    }


def _analyze_class_record(performances: list[dict], current_class: str) -> dict:
    """現クラスでの詳細実績を分析する."""
    class_perfs = [p for p in performances if p.get("grade_class") == current_class]

    if not class_perfs:
        return {
            "runs": 0,
            "best_finish": None,
            "recent_results": [],
            "trend": "初出走",
        }

    best_finish = min(p.get("finish_position", 99) for p in class_perfs)
    recent_results = [
        {
            "race_name": p.get("race_name", ""),
            "finish": p.get("finish_position", 0),
            "date": p.get("race_date", ""),
        }
        for p in class_perfs[:3]
    ]

    # トレンド判定
    if len(class_perfs) >= 2:
        recent = [p.get("finish_position", 0) for p in class_perfs[:3] if p.get("finish_position", 0) > 0]
        if len(recent) >= 2:
            if recent[0] < recent[-1]:
                trend = "上昇傾向"
            elif recent[0] > recent[-1]:
                trend = "下降傾向"
            else:
                trend = "横ばい"
        else:
            trend = "判定不可"
    else:
        trend = "サンプル不足"

    return {
        "runs": len(class_perfs),
        "best_finish": best_finish,
        "recent_results": recent_results,
        "trend": trend,
    }


def _generate_overall_comment(
    horse_name: str,
    current_class: str,
    class_stats: dict,
    class_movement: dict,
    aptitude: dict,
    class_record: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # 昇級・降級
    movement = class_movement.get("movement_type", "")
    if movement == "昇級":
        steps = class_movement.get("steps", 1)
        if steps >= 2:
            parts.append(f"{horse_name}は{steps}階級昇級で大きな壁")
        else:
            parts.append(f"{horse_name}は昇級初戦")
    elif movement == "降級":
        parts.append(f"{horse_name}は格下げで有利")

    # クラス適性
    rating = aptitude.get("rating", "")
    if rating == "A":
        parts.append(f"{current_class}クラスで実績十分")
    elif rating in ["C", "C+"]:
        parts.append(f"{current_class}クラスは初めてor苦戦中")

    # トレンド
    trend = class_record.get("trend", "")
    if trend == "上昇傾向":
        parts.append("調子上向き")
    elif trend == "下降傾向":
        parts.append("調子下降気味")

    return "。".join(parts) + "。" if parts else "クラス適性は普通。"
