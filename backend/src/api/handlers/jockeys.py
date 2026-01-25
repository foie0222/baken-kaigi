"""騎手API ハンドラー."""
import logging
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_path_parameter, get_query_parameter
from src.api.response import bad_request_response, not_found_response, success_response

logger = logging.getLogger(__name__)


def get_jockey_info(event: dict, context: Any) -> dict:
    """騎手基本情報を取得する.

    GET /jockeys/{jockey_id}/info

    Path Parameters:
        jockey_id: 騎手コード

    Returns:
        騎手基本情報
    """
    jockey_id = get_path_parameter(event, "jockey_id")
    if not jockey_id:
        return bad_request_response("jockey_id is required")

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    info = provider.get_jockey_info(jockey_id)

    if info is None:
        return not_found_response("Jockey")

    return success_response({
        "jockey_id": info.jockey_id,
        "jockey_name": info.jockey_name,
        "jockey_name_kana": info.jockey_name_kana,
        "birth_date": info.birth_date,
        "affiliation": info.affiliation,
        "license_year": info.license_year,
    })


def get_jockey_stats(event: dict, context: Any) -> dict:
    """騎手成績統計を取得する.

    GET /jockeys/{jockey_id}/stats?year=2024&period=recent

    Path Parameters:
        jockey_id: 騎手コード

    Query Parameters:
        year: 年（オプション、指定時はその年の成績）
        period: 期間（オプション、recent=直近1年, ytd=今年初から, all=通算）

    Returns:
        騎手成績統計
    """
    jockey_id = get_path_parameter(event, "jockey_id")
    if not jockey_id:
        return bad_request_response("jockey_id is required")

    # パラメータ取得
    year_str = get_query_parameter(event, "year")
    period = get_query_parameter(event, "period") or "recent"

    # yearのバリデーション
    year: int | None = None
    if year_str:
        try:
            year = int(year_str)
            if year < 1900 or year > 2100:
                return bad_request_response("year must be between 1900 and 2100")
        except ValueError:
            return bad_request_response("year must be a valid integer")

    # periodのバリデーション
    valid_periods = ["recent", "ytd", "all"]
    if period not in valid_periods:
        return bad_request_response(
            f"period must be one of: {', '.join(valid_periods)}"
        )

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    stats = provider.get_jockey_stats_detail(jockey_id, year, period)

    if stats is None:
        return not_found_response("Jockey stats")

    return success_response({
        "jockey_id": stats.jockey_id,
        "jockey_name": stats.jockey_name,
        "total_rides": stats.total_rides,
        "wins": stats.wins,
        "second_places": stats.second_places,
        "third_places": stats.third_places,
        "win_rate": stats.win_rate,
        "place_rate": stats.place_rate,
        "period": stats.period,
        "year": stats.year,
    })
