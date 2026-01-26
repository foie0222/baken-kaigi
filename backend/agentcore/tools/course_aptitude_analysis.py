"""コース適性分析ツール.

馬の競馬場・コース別の適性を分析するツール。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# 評価基準
WIN_RATE_EXCELLENT = 30.0  # 30%以上: A
WIN_RATE_GOOD = 15.0  # 15%以上: B
WIN_RATE_AVERAGE = 5.0  # 5%以上: C


@tool
def analyze_course_aptitude(
    horse_id: str,
    horse_name: str,
    venue: str = "",
    distance: int = 0,
    track_type: str = "",
    track_condition: str = "",
    horse_number: int = 0,
) -> dict:
    """馬の競馬場・コース別の適性を分析する。

    競馬場、距離、馬場状態、枠順別の成績から
    今回条件での適性を総合的に判定します。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        venue: 競馬場名
        distance: レース距離
        track_type: コース種別（芝/ダート）
        track_condition: 馬場状態（良/稍重/重/不良）
        horse_number: 馬番

    Returns:
        分析結果（競馬場適性、距離適性、馬場状態適性、枠順適性、総合評価）
    """
    try:
        # コース適性データを取得
        response = requests.get(
            f"{get_api_url()}/horses/{horse_id}/course-aptitude",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "warning": "コース適性データが見つかりませんでした",
                "horse_name": horse_name,
            }

        response.raise_for_status()
        aptitude_data = response.json()

        # 競馬場別適性
        venue_aptitude = _analyze_venue_aptitude(aptitude_data, venue)

        # 距離別適性
        distance_aptitude = _analyze_distance_aptitude(
            aptitude_data, distance
        )

        # 馬場状態別適性
        track_condition_aptitude = _analyze_track_condition_aptitude(
            aptitude_data, track_condition
        )

        # 枠順適性
        gate_position_aptitude = _analyze_gate_position_aptitude(
            aptitude_data, horse_number
        )

        # 総合評価
        overall_aptitude = _calculate_overall_aptitude(
            venue_aptitude,
            distance_aptitude,
            track_condition_aptitude,
            gate_position_aptitude,
            horse_name,
            venue,
            track_type,
            distance,
        )

        return {
            "horse_name": horse_name,
            "venue_aptitude": venue_aptitude,
            "distance_aptitude": distance_aptitude,
            "track_condition_aptitude": track_condition_aptitude,
            "gate_position_aptitude": gate_position_aptitude,
            "overall_aptitude": overall_aptitude,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze course aptitude: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze course aptitude: {e}")
        return {"error": str(e)}


def _analyze_venue_aptitude(aptitude_data: dict, venue: str) -> dict:
    """競馬場別適性を分析する."""
    by_venue = aptitude_data.get("by_venue", [])

    current_venue_data = None
    for v in by_venue:
        if v.get("venue") == venue:
            current_venue_data = v
            break

    if not current_venue_data:
        return {
            "current_venue": venue,
            "venue_record": "データなし",
            "venue_rating": "D",
            "comment": f"{venue}での出走経験なし",
        }

    starts = current_venue_data.get("starts", 0)
    wins = current_venue_data.get("wins", 0)
    places = current_venue_data.get("places", 0)
    win_rate = current_venue_data.get("win_rate", 0.0)
    place_rate = current_venue_data.get("place_rate", 0.0)

    # 着外計算
    others = max(0, starts - wins - (places - wins))
    second_third = places - wins
    venue_record = f"{wins}-{second_third}-{others}"

    rating = _calculate_rating(win_rate, starts)

    # コメント生成
    if rating == "A":
        comment = f"{venue}巧者。{starts}戦{wins}勝と相性抜群"
    elif rating == "B":
        comment = f"{venue}は得意コース"
    elif rating == "C":
        comment = f"{venue}は普通の成績"
    else:
        comment = f"{venue}はやや苦手か"

    return {
        "current_venue": venue,
        "venue_record": venue_record,
        "venue_rating": rating,
        "comment": comment,
    }


def _analyze_distance_aptitude(aptitude_data: dict, distance: int) -> dict:
    """距離別適性を分析する."""
    by_distance = aptitude_data.get("by_distance", [])
    summary = aptitude_data.get("aptitude_summary", {})

    best_distance = summary.get("best_distance", "不明")

    # 距離帯の判定
    if distance > 0:
        if distance < 1400:
            target_range = "〜1400m"
        elif distance < 1800:
            target_range = "1400-1800m"
        elif distance < 2200:
            target_range = "1800-2200m"
        else:
            target_range = "2200m〜"
    else:
        target_range = None

    # 該当距離帯のデータを検索
    distance_data = None
    for d in by_distance:
        dist_range = d.get("distance_range", "")
        if target_range and target_range in dist_range:
            distance_data = d
            break
        if distance > 0:
            # 距離範囲に含まれるかチェック
            parts = dist_range.replace("m", "").split("-")
            if len(parts) == 2:
                try:
                    min_d = int(parts[0])
                    max_d = int(parts[1])
                    if min_d <= distance <= max_d:
                        distance_data = d
                        break
                except ValueError:
                    pass

    if not distance_data:
        return {
            "current_distance": distance,
            "distance_record": "データなし",
            "distance_rating": "D",
            "best_distance": best_distance,
            "comment": f"{distance}m近辺での出走経験なし",
        }

    starts = distance_data.get("starts", 0)
    wins = distance_data.get("wins", 0)
    win_rate = distance_data.get("win_rate", 0.0)

    others = max(0, starts - wins)
    distance_record = f"{wins}-{others}"

    rating = _calculate_rating(win_rate, starts)

    # コメント生成
    if rating == "A":
        comment = f"{distance}m近辺はベスト距離"
    elif rating == "B":
        comment = f"{distance}mは適性距離内"
    else:
        best_dist_str = best_distance if best_distance != "不明" else "他の距離"
        comment = f"ベストは{best_dist_str}。{distance}mはやや長い/短い可能性"

    return {
        "current_distance": distance,
        "distance_record": distance_record,
        "distance_rating": rating,
        "best_distance": best_distance,
        "comment": comment,
    }


def _analyze_track_condition_aptitude(
    aptitude_data: dict, track_condition: str
) -> dict:
    """馬場状態別適性を分析する."""
    by_condition = aptitude_data.get("by_track_condition", [])
    summary = aptitude_data.get("aptitude_summary", {})

    best_condition = summary.get("preferred_condition", "良")

    condition_data = None
    for c in by_condition:
        if c.get("condition") == track_condition:
            condition_data = c
            break

    if not condition_data:
        return {
            "current_condition": track_condition,
            "condition_record": "データなし",
            "condition_rating": "D",
            "best_condition": best_condition,
            "comment": f"{track_condition}馬場での出走経験なし",
        }

    starts = condition_data.get("starts", 0)
    wins = condition_data.get("wins", 0)
    win_rate = condition_data.get("win_rate", 0.0)

    others = max(0, starts - wins)
    condition_record = f"{wins}-{others}"

    rating = _calculate_rating(win_rate, starts)

    # コメント生成
    if rating == "A":
        comment = f"{track_condition}馬場は得意"
    elif rating == "B":
        comment = f"{track_condition}馬場もこなせる"
    else:
        comment = f"{best_condition}馬場がベスト。{track_condition}は未知数"

    return {
        "current_condition": track_condition,
        "condition_record": condition_record,
        "condition_rating": rating,
        "best_condition": best_condition,
        "comment": comment,
    }


def _analyze_gate_position_aptitude(
    aptitude_data: dict, horse_number: int
) -> dict:
    """枠順適性を分析する."""
    by_position = aptitude_data.get("by_running_position", [])
    summary = aptitude_data.get("aptitude_summary", {})

    preferred_position = summary.get("preferred_position", "")

    # 馬番から内/外を判定
    if horse_number > 0:
        if horse_number <= 6:
            current_position = "内枠"
            current_gate = (horse_number - 1) // 2 + 1
        elif horse_number <= 12:
            current_position = "中枠"
            current_gate = (horse_number - 1) // 2 + 1
        else:
            current_position = "外枠"
            current_gate = (horse_number - 1) // 2 + 1
    else:
        current_position = "不明"
        current_gate = 0

    # 内枠と外枠の成績を集計
    inner_wins = 0
    inner_starts = 0
    outer_wins = 0
    outer_starts = 0

    for p in by_position:
        pos = p.get("position", "")
        if "内" in pos or "先行" in pos:
            inner_wins += p.get("wins", 0)
            inner_starts += p.get("starts", 0)
        elif "外" in pos or "追込" in pos:
            outer_wins += p.get("wins", 0)
            outer_starts += p.get("starts", 0)

    inner_record = f"{inner_wins}-{inner_starts - inner_wins}" if inner_starts else "データなし"
    outer_record = f"{outer_wins}-{outer_starts - outer_wins}" if outer_starts else "データなし"

    # 評価
    inner_rate = (inner_wins / inner_starts * 100) if inner_starts > 0 else 0
    outer_rate = (outer_wins / outer_starts * 100) if outer_starts > 0 else 0

    if current_position == "内枠":
        rating = _calculate_rating(inner_rate, inner_starts)
    elif current_position == "外枠":
        rating = _calculate_rating(outer_rate, outer_starts)
    else:
        rating = "B"  # 中枠はデフォルトB

    # コメント生成
    if inner_rate > outer_rate and current_position == "内枠":
        comment = f"内枠の方が成績良好。今回{horse_number}番枠は好材料"
    elif outer_rate > inner_rate and current_position == "外枠":
        comment = f"外枠の方が成績良好。今回{horse_number}番枠は好材料"
    elif current_position == "中枠":
        comment = f"中枠{horse_number}番は無難な枠順"
    else:
        comment = f"{horse_number}番枠は特に有利不利なし"

    return {
        "current_gate": current_gate,
        "current_horse_number": horse_number,
        "inner_gate_record": inner_record,
        "outer_gate_record": outer_record,
        "position_rating": rating,
        "comment": comment,
    }


def _calculate_rating(win_rate: float, starts: int) -> str:
    """勝率と出走数から評価を算出."""
    # 出走数が少ない場合は信頼度を下げる
    if starts < 2:
        return "D"

    if win_rate >= WIN_RATE_EXCELLENT:
        return "A"
    elif win_rate >= WIN_RATE_GOOD:
        return "B"
    elif win_rate >= WIN_RATE_AVERAGE:
        return "C"
    else:
        return "D"


def _calculate_overall_aptitude(
    venue_aptitude: dict,
    distance_aptitude: dict,
    track_condition_aptitude: dict,
    gate_position_aptitude: dict,
    horse_name: str,
    venue: str,
    track_type: str,
    distance: int,
) -> dict:
    """総合評価を算出する."""
    # 各評価をスコア化
    rating_scores = {"A": 4, "B": 3, "C": 2, "D": 1}

    scores = [
        rating_scores.get(venue_aptitude.get("venue_rating", "D"), 1),
        rating_scores.get(distance_aptitude.get("distance_rating", "D"), 1),
        rating_scores.get(track_condition_aptitude.get("condition_rating", "D"), 1),
        rating_scores.get(gate_position_aptitude.get("position_rating", "D"), 1),
    ]

    avg_score = sum(scores) / len(scores)
    total_score = int(avg_score * 25)  # 100点満点に変換

    # 総合評価
    if avg_score >= 3.5:
        rating = "A"
    elif avg_score >= 2.5:
        rating = "B"
    elif avg_score >= 1.5:
        rating = "C"
    else:
        rating = "D"

    # コメント生成
    a_count = scores.count(4)
    if a_count >= 3:
        comment = f"{venue}{track_type}{distance}mは絶好の条件。条件的には申し分ない"
    elif a_count >= 2:
        comment = f"条件的には合っている。好走が期待できる"
    elif a_count >= 1:
        comment = f"一部条件は良いが、総合的には普通"
    else:
        comment = f"条件的にはやや厳しいか"

    return {
        "rating": rating,
        "score": total_score,
        "comment": comment,
    }
