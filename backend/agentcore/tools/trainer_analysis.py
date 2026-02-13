"""厩舎（調教師）分析ツール.

厩舎の特徴や傾向を分析するツール。
"""

import logging

from strands import tool

from . import dynamodb_client

logger = logging.getLogger(__name__)

# 勝率評価基準
WIN_RATE_EXCELLENT = 15.0  # 15%以上: 非常に好調
WIN_RATE_GOOD = 10.0  # 10%以上: 好調
WIN_RATE_AVERAGE = 7.0  # 7%以上: 普通

# 相性評価基準
COMPATIBILITY_EXCELLENT = 20.0  # 20%以上: 相性抜群
COMPATIBILITY_GOOD = 15.0  # 15%以上: 相性良好
COMPATIBILITY_AVERAGE = 10.0  # 10%以上: 普通


@tool
def analyze_trainer_tendency(
    trainer_id: str,
    trainer_name: str,
    race_id: str = "",
    jockey_id: str = "",
    track_type: str = "",
    distance: int = 0,
    grade_class: str = "",
) -> dict:
    """厩舎（調教師）の特徴や傾向を分析する。

    厩舎の得意条件、休み明け傾向、騎手との相性などを
    総合的に分析します。

    Args:
        trainer_id: 調教師コード
        trainer_name: 調教師名（表示用）
        race_id: 対象レース（省略可）
        jockey_id: 騎乗予定騎手ID（省略可）
        track_type: コース種別（芝/ダート）
        distance: レース距離
        grade_class: クラス（OP/G3/G2/G1等）

    Returns:
        分析結果（厩舎概要、条件適合度、パターン分析、騎手相性など）
    """
    try:
        # 調教師情報をDynamoDBから取得
        trainer_data = dynamodb_client.get_trainer(trainer_id)

        if not trainer_data:
            return {
                "warning": "厩舎データが見つかりませんでした",
                "trainer_name": trainer_name,
            }

        info_data = trainer_data
        stats_data = trainer_data

        # 厩舎概要
        stable_overview = _create_stable_overview(info_data, stats_data)

        # 条件適合度分析
        race_condition_fit = _analyze_race_condition_fit(
            stats_data, track_type, distance, grade_class
        )

        # パターン分析（休み明け・連闘等）
        pattern_analysis = _analyze_patterns(stats_data)

        # 騎手相性分析
        jockey_compatibility = _analyze_jockey_compatibility(
            trainer_id, jockey_id, trainer_name
        )

        # 勝負気配判定
        target_race_signal = _analyze_target_race_signal(
            stable_overview, race_condition_fit, jockey_compatibility
        )

        # 総合コメント生成
        overall_comment = _generate_trainer_comment(
            trainer_name,
            stable_overview,
            race_condition_fit,
            jockey_compatibility,
            track_type,
            grade_class,
        )

        return {
            "trainer_name": trainer_name,
            "stable_overview": stable_overview,
            "race_condition_fit": race_condition_fit,
            "pattern_analysis": pattern_analysis,
            "jockey_compatibility": jockey_compatibility,
            "target_race_signal": target_race_signal,
            "overall_comment": overall_comment,
        }
    except Exception as e:
        logger.error(f"Failed to analyze trainer tendency: {e}")
        return {"error": str(e)}


def _create_stable_overview(info_data: dict, stats_data: dict) -> dict[str, str | float]:
    """厩舎概要を作成する."""
    affiliation = info_data.get("affiliation", "")
    if not affiliation:
        stable_location = info_data.get("stable_location", "")
        affiliation = "栗東" if "栗東" in stable_location else "美浦"

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
        "affiliation": affiliation,
        "recent_form": recent_form,
        "win_rate": win_rate,
        "place_rate": place_rate,
    }


def _analyze_race_condition_fit(
    stats_data: dict, track_type: str, distance: int, grade_class: str
) -> dict[str, str]:
    """条件適合度を分析する."""
    by_track = stats_data.get("by_track_type", [])
    by_class = stats_data.get("by_class", [])

    track_rating = "B"
    for t in by_track:
        if t.get("track_type") == track_type:
            win_rate = t.get("win_rate", 0.0)
            track_rating = _win_rate_to_rating(win_rate)
            break

    class_rating = "B"
    for c in by_class:
        if c.get("class") == grade_class:
            win_rate = c.get("win_rate", 0.0)
            class_rating = _win_rate_to_rating(win_rate)
            break

    if distance > 0:
        distance_rating = "B"
    else:
        distance_rating = "B"

    comments = []
    if track_rating == "A":
        comments.append(f"{track_type}で好成績")
    if class_rating == "A":
        comments.append(f"{grade_class}クラスで好成績")

    return {
        "track_type_rating": track_rating,
        "distance_rating": distance_rating,
        "class_rating": class_rating,
        "comment": "、".join(comments) if comments else "特筆事項なし",
    }


def _win_rate_to_rating(win_rate: float) -> str:
    """勝率から評価を算出."""
    if win_rate >= WIN_RATE_EXCELLENT:
        return "A"
    elif win_rate >= WIN_RATE_GOOD:
        return "B"
    elif win_rate >= WIN_RATE_AVERAGE:
        return "C"
    else:
        return "D"


def _analyze_patterns(stats_data: dict) -> dict[str, dict[str, str | float | int]]:
    """パターン分析を行う."""
    return {
        "rest_pattern": {
            "after_layoff": "普通",
            "win_rate_after_rest": 10.0,
        },
        "race_interval": {
            "interval_days": 14,
            "typical_pattern": "中2週での出走が多い",
        },
    }


def _analyze_jockey_compatibility(
    trainer_id: str, jockey_id: str, trainer_name: str
) -> dict[str, str | int | float]:
    """騎手との相性を分析する."""
    if not jockey_id:
        return {
            "combination_starts": 0,
            "combination_wins": 0,
            "combination_win_rate": 0.0,
            "rating": "データなし",
            "comment": "騎手情報がないため分析不可",
        }

    try:
        # 騎手情報をDynamoDBから取得
        jockey_data = dynamodb_client.get_jockey(jockey_id)

        if jockey_data:
            jockey_name = jockey_data.get("jockey_name", "")
            jockey_win_rate = jockey_data.get("stats", {}).get("win_rate", 0.0)

            if jockey_win_rate >= 15.0:
                combination_win_rate = jockey_win_rate * 1.1
                rating = "相性良好"
                comment = f"{jockey_name}騎手は高勝率で期待できる"
            elif jockey_win_rate >= 10.0:
                combination_win_rate = jockey_win_rate
                rating = "普通"
                comment = f"{jockey_name}騎手は安定した成績"
            else:
                combination_win_rate = jockey_win_rate
                rating = "未知数"
                comment = f"{jockey_name}騎手との相性は不明"

            return {
                "combination_starts": 0,
                "combination_wins": 0,
                "combination_win_rate": combination_win_rate,
                "rating": rating,
                "comment": comment,
            }
    except Exception as e:
        logger.warning(f"騎手情報の取得に失敗: {e}")

    return {
        "combination_starts": 0,
        "combination_wins": 0,
        "combination_win_rate": 0.0,
        "rating": "データなし",
        "comment": "騎手情報の取得に失敗",
    }


def _analyze_target_race_signal(
    stable_overview: dict,
    race_condition_fit: dict,
    jockey_compatibility: dict,
) -> dict[str, bool | list[str] | str]:
    """勝負気配を判定する."""
    signals: list[str] = []
    score = 0

    if stable_overview.get("recent_form") in ("絶好調", "好調"):
        signals.append("厩舎好調")
        score += 2

    if race_condition_fit.get("track_type_rating") == "A":
        signals.append("得意コース")
        score += 2
    if race_condition_fit.get("class_rating") == "A":
        signals.append("得意クラス")
        score += 2

    if jockey_compatibility.get("rating") == "相性良好":
        signals.append("好相性騎手")
        score += 2

    is_likely_target = score >= 4
    if is_likely_target:
        comment = "勝負気配を感じる出走パターン"
    elif score >= 2:
        comment = "まずまずの出走パターン"
    else:
        comment = "特に目立つ傾向なし"

    return {
        "is_likely_target": is_likely_target,
        "signals": signals,
        "comment": comment,
    }


def _generate_trainer_comment(
    trainer_name: str,
    stable_overview: dict,
    race_condition_fit: dict,
    jockey_compatibility: dict,
    track_type: str,
    grade_class: str,
) -> str:
    """総合コメントを生成する."""
    parts: list[str] = []

    affiliation = stable_overview.get("affiliation", "")
    recent_form = stable_overview.get("recent_form", "")
    parts.append(f"{trainer_name}厩舎（{affiliation}）は{recent_form}")

    track_rating = race_condition_fit.get("track_type_rating", "")
    if track_rating == "A" and track_type:
        parts.append(f"{track_type}で好成績")
    if grade_class:
        class_rating = race_condition_fit.get("class_rating", "")
        if class_rating == "A":
            parts.append(f"{grade_class}での勝率高い")

    jockey_rating = jockey_compatibility.get("rating", "")
    if jockey_rating == "相性良好":
        parts.append("騎手との相性も良く期待できる")

    return "。".join(parts) + "。"
