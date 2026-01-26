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


def _format_record(wins: int, seconds: int, thirds: int, others: int) -> str:
    """成績を「勝-2着-3着-着外」形式でフォーマットする.

    Args:
        wins: 勝利数
        seconds: 2着数
        thirds: 3着数
        others: 着外数

    Returns:
        フォーマットされた成績文字列
    """
    return f"{wins}-{seconds}-{thirds}-{others}"


def _analyze_venue_aptitude(aptitude_data: dict, venue: str) -> dict[str, str]:
    """競馬場別適性を分析する.

    Args:
        aptitude_data: コース適性データ
        venue: 対象競馬場名

    Returns:
        競馬場適性分析結果
    """
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
    places = current_venue_data.get("places", 0)  # 複勝圏内（1-3着）
    win_rate = current_venue_data.get("win_rate", 0.0)

    # 2着と3着の数を推定（places = 1着 + 2着 + 3着）
    second_third = max(0, places - wins)
    # 2着と3着を分けられない場合は2着に寄せる
    seconds = second_third // 2 + second_third % 2
    thirds = second_third - seconds
    others = max(0, starts - places)
    venue_record = _format_record(wins, seconds, thirds, others)

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


def _analyze_distance_aptitude(aptitude_data: dict, distance: int) -> dict[str, str | int]:
    """距離別適性を分析する.

    Args:
        aptitude_data: コース適性データ
        distance: 対象距離

    Returns:
        距離適性分析結果
    """
    by_distance = aptitude_data.get("by_distance", [])
    summary = aptitude_data.get("aptitude_summary") or {}

    best_distance = summary.get("best_distance", "不明") if summary else "不明"

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
            # 距離範囲に含まれるかチェック（"1600m以下" 形式にも対応）
            if "以下" in dist_range:
                try:
                    max_d = int(dist_range.replace("m以下", ""))
                    if distance <= max_d:
                        distance_data = d
                        break
                except ValueError:
                    logger.debug(f"距離範囲のパースに失敗: {dist_range}")
            elif "以上" in dist_range:
                try:
                    min_d = int(dist_range.replace("m以上", ""))
                    if distance >= min_d:
                        distance_data = d
                        break
                except ValueError:
                    logger.debug(f"距離範囲のパースに失敗: {dist_range}")
            else:
                # "1600-2000m" 形式
                parts = dist_range.replace("m", "").split("-")
                if len(parts) == 2:
                    try:
                        min_d = int(parts[0])
                        max_d = int(parts[1])
                        if min_d <= distance <= max_d:
                            distance_data = d
                            break
                    except ValueError:
                        logger.debug(f"距離範囲のパースに失敗: {dist_range}")

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
    places = distance_data.get("places", 0)
    win_rate = distance_data.get("win_rate", 0.0)

    second_third = max(0, places - wins) if places else 0
    seconds = second_third // 2 + second_third % 2
    thirds = second_third - seconds
    others = max(0, starts - (wins + second_third))
    distance_record = _format_record(wins, seconds, thirds, others)

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
) -> dict[str, str]:
    """馬場状態別適性を分析する.

    Args:
        aptitude_data: コース適性データ
        track_condition: 対象馬場状態

    Returns:
        馬場状態適性分析結果
    """
    by_condition = aptitude_data.get("by_track_condition", [])
    summary = aptitude_data.get("aptitude_summary") or {}

    best_condition = summary.get("preferred_condition", "良") if summary else "良"

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
    places = condition_data.get("places", 0)
    win_rate = condition_data.get("win_rate", 0.0)

    second_third = max(0, places - wins) if places else 0
    seconds = second_third // 2 + second_third % 2
    thirds = second_third - seconds
    others = max(0, starts - (wins + second_third))
    condition_record = _format_record(wins, seconds, thirds, others)

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
) -> dict[str, str | int]:
    """枠順適性を分析する.

    Args:
        aptitude_data: コース適性データ
        horse_number: 馬番

    Returns:
        枠順適性分析結果
    """
    by_position = aptitude_data.get("by_running_position", [])

    # 馬番から内/中/外枠を判定
    # JRAの枠番は1-8（フルゲート18頭の場合）
    if horse_number > 0:
        if horse_number <= 6:
            current_position = "内枠(1-4)"
            current_gate = min((horse_number - 1) // 2 + 1, 8)  # 枠番は最大8
        elif horse_number <= 12:
            current_position = "中枠(5-6)"
            current_gate = min((horse_number - 1) // 2 + 1, 8)
        else:
            current_position = "外枠(7-8)"
            current_gate = min((horse_number - 1) // 2 + 1, 8)
    else:
        current_position = "不明"
        current_gate = 0

    # 内枠と外枠の成績を集計（枠順データのみ参照、脚質データは除外）
    inner_wins = 0
    inner_starts = 0
    inner_places = 0
    middle_wins = 0
    middle_starts = 0
    middle_places = 0
    outer_wins = 0
    outer_starts = 0
    outer_places = 0

    for p in by_position:
        pos = p.get("position", "")
        # 枠順データのみを参照（「内枠」「外枠」等）、脚質データ（「先行」「追込」）は除外
        if "枠" not in pos:
            continue
        if "内枠" in pos:
            inner_wins += p.get("wins", 0)
            inner_starts += p.get("starts", 0)
            inner_places += p.get("places", 0)
        elif "中枠" in pos:
            middle_wins += p.get("wins", 0)
            middle_starts += p.get("starts", 0)
            middle_places += p.get("places", 0)
        elif "外枠" in pos:
            outer_wins += p.get("wins", 0)
            outer_starts += p.get("starts", 0)
            outer_places += p.get("places", 0)

    def format_gate_record(wins: int, starts: int, places: int) -> str:
        if starts == 0:
            return "データなし"
        second_third = max(0, places - wins)
        seconds = second_third // 2 + second_third % 2
        thirds = second_third - seconds
        others = max(0, starts - places)
        return _format_record(wins, seconds, thirds, others)

    inner_record = format_gate_record(inner_wins, inner_starts, inner_places)
    outer_record = format_gate_record(outer_wins, outer_starts, outer_places)

    # 評価
    inner_rate = (inner_wins / inner_starts * 100) if inner_starts > 0 else 0
    middle_rate = (middle_wins / middle_starts * 100) if middle_starts > 0 else 0
    outer_rate = (outer_wins / outer_starts * 100) if outer_starts > 0 else 0

    if "内枠" in current_position:
        rating = _calculate_rating(inner_rate, inner_starts)
    elif "外枠" in current_position:
        rating = _calculate_rating(outer_rate, outer_starts)
    elif "中枠" in current_position:
        # 中枠の場合もAPIデータから評価
        rating = _calculate_rating(middle_rate, middle_starts)
    else:
        rating = "D"  # 枠不明の場合

    # コメント生成
    if inner_rate > outer_rate and "内枠" in current_position:
        comment = f"内枠の方が成績良好。今回{horse_number}番枠は好材料"
    elif outer_rate > inner_rate and "外枠" in current_position:
        comment = f"外枠の方が成績良好。今回{horse_number}番枠は好材料"
    elif "中枠" in current_position:
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
    """勝率と出走数から評価を算出する.

    Args:
        win_rate: 勝率（%）
        starts: 出走数

    Returns:
        評価（A/B/C/D）
    """
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
) -> dict[str, str | int]:
    """総合評価を算出する.

    Args:
        venue_aptitude: 競馬場適性
        distance_aptitude: 距離適性
        track_condition_aptitude: 馬場状態適性
        gate_position_aptitude: 枠順適性
        horse_name: 馬名
        venue: 競馬場名
        track_type: コース種別
        distance: 距離

    Returns:
        総合評価結果
    """
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

    # コメント生成（track_typeも使用）
    track_info = f"{track_type}" if track_type else ""
    a_count = scores.count(4)
    if a_count >= 3:
        comment = f"{venue}{track_info}{distance}mは絶好の条件。条件的には申し分ない"
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
