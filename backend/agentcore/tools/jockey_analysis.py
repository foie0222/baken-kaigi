"""騎手分析ツール.

騎手の特徴・得意条件・馬との相性を分析するツール。
"""

import logging

from strands import tool

from . import dynamodb_client

logger = logging.getLogger(__name__)

# 評価基準
WIN_RATE_EXCELLENT = 18.0  # 18%以上
WIN_RATE_GOOD = 12.0  # 12%以上
WIN_RATE_AVERAGE = 8.0  # 8%以上


@tool
def analyze_jockey_factor(
    jockey_id: str,
    jockey_name: str,
    horse_id: str = "",
    horse_name: str = "",
    venue: str = "",
    track_type: str = "",
    distance: int = 0,
    popularity: int = 0,
) -> dict:
    """騎手の特徴・得意条件・馬との相性を分析する。

    騎手の直近成績、コース適性、馬との相性、
    人気別信頼度などを総合的に分析します。

    Args:
        jockey_id: 騎手コード
        jockey_name: 騎手名（表示用）
        horse_id: 馬コード（相性分析用）
        horse_name: 馬名（表示用）
        venue: 競馬場名
        track_type: コース種別（芝/ダート）
        distance: レース距離
        popularity: 予想人気

    Returns:
        分析結果（概要、コース成績、馬との相性、人気別信頼度など）
    """
    try:
        # 騎手情報をDynamoDBから取得
        jockey_data = dynamodb_client.get_jockey(jockey_id)

        if not jockey_data:
            return {
                "warning": "騎手データが見つかりませんでした",
                "jockey_name": jockey_name,
            }

        stats_data = jockey_data

        # 騎手概要
        jockey_overview = _create_jockey_overview(stats_data)

        # コース成績分析
        course_performance = _analyze_course_performance(
            stats_data, venue, track_type, distance
        )

        # 馬との相性分析
        horse_compatibility = _analyze_horse_compatibility(
            jockey_id, horse_id, horse_name
        )

        # 乗り替わり分析（簡易版）
        jockey_change_analysis = _analyze_jockey_change()

        # 人気別信頼度
        popularity_reliability = _analyze_popularity_reliability(
            stats_data, popularity
        )

        # 総合コメント生成
        overall_comment = _generate_jockey_comment(
            jockey_name,
            jockey_overview,
            course_performance,
            horse_compatibility,
            popularity_reliability,
            venue,
            track_type,
            distance,
            popularity,
        )

        return {
            "jockey_name": jockey_name,
            "jockey_overview": jockey_overview,
            "course_performance": course_performance,
            "horse_compatibility": horse_compatibility,
            "jockey_change_analysis": jockey_change_analysis,
            "popularity_reliability": popularity_reliability,
            "overall_comment": overall_comment,
        }
    except Exception as e:
        logger.error(f"Failed to analyze jockey factor: {e}")
        return {"error": str(e)}


def _create_jockey_overview(stats_data: dict) -> dict[str, str | float | int]:
    """騎手概要を作成する."""
    stats = stats_data.get("stats", {})
    win_rate = stats.get("win_rate", 0.0)
    place_rate = stats.get("place_rate", 0.0)

    if win_rate >= WIN_RATE_EXCELLENT:
        recent_form = "絶好調"
    elif win_rate >= WIN_RATE_GOOD:
        recent_form = "好調"
    elif win_rate >= WIN_RATE_AVERAGE:
        recent_form = "普通"
    else:
        recent_form = "低調"

    return {
        "recent_form": recent_form,
        "recent_win_rate": win_rate,
        "recent_place_rate": place_rate,
        "ranking": 0,
    }


def _analyze_course_performance(
    stats_data: dict, venue: str, track_type: str, distance: int
) -> dict[str, str | float | int]:
    """コース成績を分析する."""
    by_venue = stats_data.get("by_venue", [])
    by_track = stats_data.get("by_track_type", [])

    venue_data = None
    for v in by_venue:
        if v.get("venue") == venue:
            venue_data = v
            break

    track_data = None
    for t in by_track:
        if t.get("track_type") == track_type:
            track_data = t
            break

    venue_win_rate = venue_data.get("win_rate", 0.0) if venue_data else 0.0
    track_win_rate = track_data.get("win_rate", 0.0) if track_data else 0.0

    best_win_rate = max(venue_win_rate, track_win_rate)

    if best_win_rate >= WIN_RATE_EXCELLENT:
        rating = "A"
    elif best_win_rate >= WIN_RATE_GOOD:
        rating = "B"
    elif best_win_rate >= WIN_RATE_AVERAGE:
        rating = "C"
    else:
        rating = "D"

    if venue_data:
        starts = venue_data.get("starts", 0)
        wins = venue_data.get("wins", 0)
        places = venue_data.get("places", 0)
        others = max(0, starts - places)
        record = f"{wins}-{places - wins}-{others}"
    else:
        record = "データなし"

    if rating == "A":
        comment = f"{venue}{track_type}は得意コース"
    elif rating == "B":
        comment = f"{venue}{track_type}は相性良好"
    elif rating == "C":
        comment = f"{venue}{track_type}は普通の成績"
    else:
        comment = f"{venue}{track_type}はやや苦手か"

    return {
        "venue": venue,
        "track_type": track_type,
        "distance": distance,
        "record": record,
        "win_rate": best_win_rate,
        "rating": rating,
        "comment": comment,
    }


def _analyze_horse_compatibility(
    jockey_id: str, horse_id: str, horse_name: str
) -> dict[str, str | float | list]:
    """馬との相性を分析する."""
    if not horse_id:
        return {
            "combination_history": [],
            "combination_record": "データなし",
            "combination_win_rate": 0.0,
            "rating": "不明",
            "comment": "馬情報がないため分析不可",
        }

    try:
        # 馬の過去成績をDynamoDBから取得
        performances = dynamodb_client.get_horse_performances(horse_id, limit=20)

        if performances:
            combination_races = []
            wins = 0
            places = 0
            for p in performances:
                perf_jockey_id = p.get("jockey_id", "")
                if perf_jockey_id and perf_jockey_id == jockey_id:
                    finish = p.get("finish_position", 0)
                    combination_races.append({
                        "date": p.get("race_date", ""),
                        "result": f"{finish}着",
                        "race": p.get("race_name", ""),
                    })
                    if finish == 1:
                        wins += 1
                    if finish <= 3:
                        places += 1

            if combination_races:
                total = len(combination_races)
                others = total - places
                combination_record = f"{wins}-{places - wins}-{others}"
                combination_win_rate = (wins / total * 100) if total > 0 else 0.0

                if combination_win_rate >= 50.0:
                    rating = "抜群"
                elif combination_win_rate >= 25.0:
                    rating = "良好"
                elif combination_win_rate >= 10.0:
                    rating = "普通"
                else:
                    rating = "不明"

                comment = f"{horse_name}とのコンビは{total}戦{wins}勝"

                return {
                    "combination_history": combination_races[:5],
                    "combination_record": combination_record,
                    "combination_win_rate": combination_win_rate,
                    "rating": rating,
                    "comment": comment,
                }
    except Exception as e:
        logger.warning(f"馬の過去成績取得に失敗（初騎乗として処理）: {e}")

    return {
        "combination_history": [],
        "combination_record": "初騎乗",
        "combination_win_rate": 0.0,
        "rating": "未知数",
        "comment": f"{horse_name}とは初コンビ",
    }


def _analyze_jockey_change() -> dict[str, str | bool]:
    """乗り替わり分析（簡易版）."""
    return {
        "is_change": False,
        "previous_jockey": "",
        "change_reason_guess": "",
        "change_impact": "判定不能",
        "comment": "乗り替わり情報なし",
    }


def _analyze_popularity_reliability(stats_data: dict, popularity: int) -> dict[str, str | float | int]:
    """人気別信頼度を分析する."""
    by_popularity = stats_data.get("by_popularity", [])

    if popularity <= 0:
        return {
            "current_popularity": popularity,
            "win_rate_at_popularity": 0.0,
            "rating": "データなし",
            "comment": "人気データなし",
        }

    pop_data = None
    for p in by_popularity:
        if p.get("popularity") == popularity:
            pop_data = p
            break

    if not pop_data:
        if popularity <= 3:
            pop_range = "1-3番人気"
        elif popularity <= 6:
            pop_range = "4-6番人気"
        else:
            pop_range = "7番人気以下"

        for p in by_popularity:
            if pop_range in str(p.get("popularity_range", "")):
                pop_data = p
                break

    if not pop_data:
        return {
            "current_popularity": popularity,
            "win_rate_at_popularity": 0.0,
            "rating": "データなし",
            "comment": f"{popularity}番人気での成績データなし",
        }

    win_rate = pop_data.get("win_rate", 0.0)

    if popularity <= 3:
        if win_rate >= 25.0:
            rating = "信頼できる"
        elif win_rate >= 15.0:
            rating = "普通"
        else:
            rating = "やや不安"
    else:
        if win_rate >= 10.0:
            rating = "穴狙い向き"
        elif win_rate >= 5.0:
            rating = "普通"
        else:
            rating = "不安"

    if popularity <= 3:
        comment = f"上位人気での勝率{win_rate:.1f}%"
    elif popularity <= 6:
        comment = f"中穴での好走率が{'高い' if win_rate >= 10.0 else '普通'}騎手"
    else:
        comment = f"人気薄での激走{'あり' if win_rate >= 5.0 else '少なめ'}"

    return {
        "current_popularity": popularity,
        "win_rate_at_popularity": win_rate,
        "rating": rating,
        "comment": comment,
    }


def _generate_jockey_comment(
    jockey_name: str,
    jockey_overview: dict,
    course_performance: dict,
    horse_compatibility: dict,
    popularity_reliability: dict,
    venue: str,
    track_type: str,
    distance: int,
    popularity: int,
) -> str:
    """総合コメントを生成する."""
    parts = []

    course_rating = course_performance.get("rating", "")
    if course_rating == "A":
        parts.append(f"{venue}{track_type}は得意")
    elif course_rating == "B":
        parts.append(f"{venue}{track_type}は相性良好")

    horse_rating = horse_compatibility.get("rating", "")
    if horse_rating in ("抜群", "良好"):
        parts.append("この馬との相性も良い")
    elif horse_rating == "未知数":
        parts.append("この馬とは初コンビ")

    pop_rating = popularity_reliability.get("rating", "")
    if popularity > 0:
        if pop_rating == "信頼できる":
            parts.append(f"{popularity}番人気なら期待できる")
        elif pop_rating == "穴狙い向き":
            parts.append(f"{popularity}番人気でも狙える")

    if not parts:
        return f"{jockey_name}騎手は今回特筆事項なし。"

    return "。".join(parts) + "。"
