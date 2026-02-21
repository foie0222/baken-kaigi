"""馬主・生産者API ハンドラー."""
import logging
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_path_parameter, get_query_parameter
from src.api.response import bad_request_response, internal_error_response, not_found_response, success_response

logger = logging.getLogger(__name__)


def get_owner_info(event: dict, context: Any) -> dict:
    """馬主基本情報を取得する.

    GET /owners/{owner_id}

    Path Parameters:
        owner_id: 馬主コード

    Returns:
        馬主基本情報
    """
    owner_id = get_path_parameter(event, "owner_id")
    if not owner_id:
        return bad_request_response("owner_id is required", event=event)

    try:
        provider = Dependencies.get_race_data_provider()
        result = provider.get_owner_info(owner_id)
    except Exception:
        logger.exception("Failed to get owner info for owner_id=%s", owner_id)
        return internal_error_response(event=event)

    if result is None:
        return not_found_response("Owner", event=event)

    response = {
        "owner_id": result.owner_id,
        "owner_name": result.owner_name,
        "representative_name": result.representative_name,
        "registered_year": result.registered_year,
    }

    return success_response(response, event=event)


def get_owner_stats(event: dict, context: Any) -> dict:
    """馬主成績統計を取得する.

    GET /owners/{owner_id}/stats?year=2024&period=all

    Path Parameters:
        owner_id: 馬主コード

    Query Parameters:
        year: 年（オプション）
        period: 期間（recent=直近1年, all=通算）デフォルト: all

    Returns:
        馬主成績統計
    """
    owner_id = get_path_parameter(event, "owner_id")
    if not owner_id:
        return bad_request_response("owner_id is required", event=event)

    year_str = get_query_parameter(event, "year")
    period = get_query_parameter(event, "period") or "all"

    year: int | None = None
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            return bad_request_response("Invalid year format", event=event)
        if not (1900 <= year <= 2100):
            return bad_request_response("year must be between 1900 and 2100", event=event)

    if period not in ("recent", "all"):
        return bad_request_response("period must be 'recent' or 'all'", event=event)

    try:
        provider = Dependencies.get_race_data_provider()
        result = provider.get_owner_stats(owner_id, year=year, period=period)
    except Exception:
        logger.exception("Failed to get owner stats for owner_id=%s", owner_id)
        return internal_error_response(event=event)

    if result is None:
        return not_found_response("Owner stats", event=event)

    response = {
        "owner_id": result.owner_id,
        "owner_name": result.owner_name,
        "total_horses": result.total_horses,
        "total_starts": result.total_starts,
        "wins": result.wins,
        "second_places": result.second_places,
        "third_places": result.third_places,
        "win_rate": result.win_rate,
        "place_rate": result.place_rate,
        "total_prize": result.total_prize,
        "g1_wins": result.g1_wins,
        "period": result.period,
        "year": result.year,
    }

    return success_response(response, event=event)


def get_breeder_info(event: dict, context: Any) -> dict:
    """生産者基本情報を取得する.

    GET /breeders/{breeder_id}

    Path Parameters:
        breeder_id: 生産者コード

    Returns:
        生産者基本情報
    """
    breeder_id = get_path_parameter(event, "breeder_id")
    if not breeder_id:
        return bad_request_response("breeder_id is required", event=event)

    try:
        provider = Dependencies.get_race_data_provider()
        result = provider.get_breeder_info(breeder_id)
    except Exception:
        logger.exception("Failed to get breeder info for breeder_id=%s", breeder_id)
        return internal_error_response(event=event)

    if result is None:
        return not_found_response("Breeder", event=event)

    response = {
        "breeder_id": result.breeder_id,
        "breeder_name": result.breeder_name,
        "location": result.location,
        "registered_year": result.registered_year,
    }

    return success_response(response, event=event)


def get_breeder_stats(event: dict, context: Any) -> dict:
    """生産者成績統計を取得する.

    GET /breeders/{breeder_id}/stats?year=2024&period=all

    Path Parameters:
        breeder_id: 生産者コード

    Query Parameters:
        year: 年（オプション）
        period: 期間（recent=直近1年, all=通算）デフォルト: all

    Returns:
        生産者成績統計
    """
    breeder_id = get_path_parameter(event, "breeder_id")
    if not breeder_id:
        return bad_request_response("breeder_id is required", event=event)

    year_str = get_query_parameter(event, "year")
    period = get_query_parameter(event, "period") or "all"

    year: int | None = None
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            return bad_request_response("Invalid year format", event=event)
        if not (1900 <= year <= 2100):
            return bad_request_response("year must be between 1900 and 2100", event=event)

    if period not in ("recent", "all"):
        return bad_request_response("period must be 'recent' or 'all'", event=event)

    try:
        provider = Dependencies.get_race_data_provider()
        result = provider.get_breeder_stats(breeder_id, year=year, period=period)
    except Exception:
        logger.exception("Failed to get breeder stats for breeder_id=%s", breeder_id)
        return internal_error_response(event=event)

    if result is None:
        return not_found_response("Breeder stats", event=event)

    response = {
        "breeder_id": result.breeder_id,
        "breeder_name": result.breeder_name,
        "total_horses": result.total_horses,
        "total_starts": result.total_starts,
        "wins": result.wins,
        "second_places": result.second_places,
        "third_places": result.third_places,
        "win_rate": result.win_rate,
        "place_rate": result.place_rate,
        "total_prize": result.total_prize,
        "g1_wins": result.g1_wins,
        "period": result.period,
        "year": result.year,
    }

    return success_response(response, event=event)
