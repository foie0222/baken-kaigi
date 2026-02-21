"""種牡馬（スタリオン）API ハンドラー."""
import logging
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_path_parameter, get_query_parameter
from src.api.response import bad_request_response, internal_error_response, not_found_response, success_response

logger = logging.getLogger(__name__)


def get_stallion_offspring_stats(event: dict, context: Any) -> dict:
    """種牡馬の産駒成績統計を取得する.

    GET /stallions/{stallion_id}/offspring-stats

    Path Parameters:
        stallion_id: 種牡馬コード（馬ID）

    Query Parameters:
        year: 集計年度（省略時は通算）
        track_type: 芝/ダート/障害 でフィルタ

    Returns:
        産駒成績統計
    """
    stallion_id = get_path_parameter(event, "stallion_id")
    if not stallion_id:
        return bad_request_response("stallion_id is required", event=event)

    # パラメータ取得
    year_str = get_query_parameter(event, "year")
    track_type = get_query_parameter(event, "track_type")

    # yearのバリデーション
    year: int | None = None
    if year_str:
        try:
            year = int(year_str)
            if year < 1970 or year > 2100:
                return bad_request_response("year must be between 1970 and 2100", event=event)
        except ValueError:
            return bad_request_response("year must be a valid integer", event=event)

    # track_typeのバリデーション
    valid_track_types = ["芝", "ダート", "障害"]
    if track_type and track_type not in valid_track_types:
        return bad_request_response(
            f"track_type must be one of: {', '.join(valid_track_types)}",
            event=event,
        )

    # プロバイダから取得
    try:
        provider = Dependencies.get_race_data_provider()
        stats, track_stats, distance_stats, condition_stats, top_offspring = (
            provider.get_stallion_offspring_stats(stallion_id, year, track_type)
        )
    except Exception:
        logger.exception("Failed to get stallion offspring stats for stallion_id=%s", stallion_id)
        return internal_error_response(event=event)

    if not stats:
        return not_found_response("Stallion", event=event)

    return success_response({
        "stallion_id": stats.stallion_id,
        "stallion_name": stats.stallion_name,
        "total_offspring": stats.total_offspring,
        "stats": {
            "total_starts": stats.total_starts,
            "wins": stats.wins,
            "win_rate": stats.win_rate,
            "place_rate": stats.place_rate,
            "g1_wins": stats.g1_wins,
            "earnings": stats.earnings,
        },
        "by_track_type": [
            {
                "track_type": t.track_type,
                "starts": t.starts,
                "wins": t.wins,
                "win_rate": t.win_rate,
                "avg_distance": t.avg_distance,
            }
            for t in track_stats
        ],
        "by_distance": [
            {
                "distance_range": d.distance_range,
                "starts": d.starts,
                "wins": d.wins,
                "win_rate": d.win_rate,
            }
            for d in distance_stats
        ],
        "by_track_condition": [
            {
                "condition": c.condition,
                "starts": c.starts,
                "wins": c.wins,
                "win_rate": c.win_rate,
            }
            for c in condition_stats
        ],
        "top_offspring": [
            {
                "horse_name": o.horse_name,
                "wins": o.wins,
                "g1_wins": o.g1_wins,
            }
            for o in top_offspring
        ],
    }, event=event)
