"""厩舎（調教師）API ハンドラー."""
import logging
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_path_parameter, get_query_parameter
from src.api.response import bad_request_response, internal_error_response, not_found_response, success_response

logger = logging.getLogger(__name__)


def get_trainer_info(event: dict, context: Any) -> dict:
    """厩舎（調教師）基本情報を取得する.

    GET /trainers/{trainer_id}/info

    Path Parameters:
        trainer_id: 調教師コード

    Returns:
        厩舎基本情報
    """
    trainer_id = get_path_parameter(event, "trainer_id")
    if not trainer_id:
        return bad_request_response("trainer_id is required", event=event)

    # プロバイダから取得
    try:
        provider = Dependencies.get_race_data_provider()
        trainer_info = provider.get_trainer_info(trainer_id)
    except Exception:
        logger.exception("Failed to get trainer info for trainer_id=%s", trainer_id)
        return internal_error_response(event=event)

    if not trainer_info:
        return not_found_response("Trainer", event=event)

    return success_response({
        "trainer_id": trainer_info.trainer_id,
        "trainer_name": trainer_info.trainer_name,
        "trainer_name_kana": trainer_info.trainer_name_kana,
        "affiliation": trainer_info.affiliation,
        "stable_location": trainer_info.stable_location,
        "license_year": trainer_info.license_year,
        "career_wins": trainer_info.career_wins,
        "career_starts": trainer_info.career_starts,
    }, event=event)


def get_trainer_stats(event: dict, context: Any) -> dict:
    """厩舎（調教師）成績統計を取得する.

    GET /trainers/{trainer_id}/stats

    Path Parameters:
        trainer_id: 調教師コード

    Query Parameters:
        year: 集計年度（省略時は通算）
        period: recent（直近1年）/ all（通算）

    Returns:
        厩舎成績統計
    """
    trainer_id = get_path_parameter(event, "trainer_id")
    if not trainer_id:
        return bad_request_response("trainer_id is required", event=event)

    # パラメータ取得
    year_str = get_query_parameter(event, "year")
    period = get_query_parameter(event, "period") or "all"

    # yearのバリデーション
    year = None
    if year_str:
        try:
            year = int(year_str)
            if year < 1900 or year > 2100:
                return bad_request_response("year must be between 1900 and 2100", event=event)
        except ValueError:
            return bad_request_response("year must be a valid integer", event=event)

    # periodのバリデーション
    valid_periods = ["recent", "all"]
    if period not in valid_periods:
        return bad_request_response(
            f"period must be one of: {', '.join(valid_periods)}",
            event=event,
        )

    # プロバイダから取得
    try:
        provider = Dependencies.get_race_data_provider()
        stats, track_stats, class_stats = provider.get_trainer_stats_detail(
            trainer_id, year, period
        )
    except Exception:
        logger.exception("Failed to get trainer stats for trainer_id=%s", trainer_id)
        return internal_error_response(event=event)

    if not stats:
        return not_found_response("Trainer stats", event=event)

    return success_response({
        "trainer_id": stats.trainer_id,
        "trainer_name": stats.trainer_name,
        "stats": {
            "total_starts": stats.total_starts,
            "wins": stats.wins,
            "places": stats.wins + stats.second_places + stats.third_places,
            "win_rate": stats.win_rate,
            "place_rate": stats.place_rate,
            "prize_money": stats.prize_money,
        },
        "by_track_type": [
            {
                "track_type": t.track_type,
                "starts": t.starts,
                "wins": t.wins,
                "win_rate": t.win_rate,
            }
            for t in track_stats
        ],
        "by_class": [
            {
                "class": c.grade_class,
                "starts": c.starts,
                "wins": c.wins,
                "win_rate": c.win_rate,
            }
            for c in class_stats
        ],
    }, event=event)
