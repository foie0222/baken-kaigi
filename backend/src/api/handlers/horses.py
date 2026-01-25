"""馬API ハンドラー."""
import logging
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_path_parameter, get_query_parameter
from src.api.response import bad_request_response, success_response

logger = logging.getLogger(__name__)


def get_horse_performances(event: dict, context: Any) -> dict:
    """馬の過去成績を取得する.

    GET /horses/{horse_id}/performances

    Path Parameters:
        horse_id: 馬コード

    Query Parameters:
        limit: 取得件数（デフォルト: 5、最大: 20）
        track_type: 芝/ダート/障害 でフィルタ

    Returns:
        馬の過去成績一覧
    """
    horse_id = get_path_parameter(event, "horse_id")
    if not horse_id:
        return bad_request_response("horse_id is required")

    # パラメータ取得
    limit_str = get_query_parameter(event, "limit")
    track_type = get_query_parameter(event, "track_type")

    # limitのバリデーション
    limit = 5
    if limit_str:
        try:
            limit = int(limit_str)
            if limit < 1 or limit > 20:
                return bad_request_response("limit must be between 1 and 20")
        except ValueError:
            return bad_request_response("limit must be a valid integer")

    # track_typeのバリデーション
    valid_track_types = ["芝", "ダート", "障害"]
    if track_type and track_type not in valid_track_types:
        return bad_request_response(
            f"track_type must be one of: {', '.join(valid_track_types)}"
        )

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    performances = provider.get_horse_performances(horse_id, limit, track_type)

    return success_response({
        "horse_id": horse_id,
        "performances": [
            {
                "race_id": p.race_id,
                "race_date": p.race_date,
                "race_name": p.race_name,
                "venue": p.venue,
                "distance": p.distance,
                "track_type": p.track_type,
                "track_condition": p.track_condition,
                "finish_position": p.finish_position,
                "total_runners": p.total_runners,
                "time": p.time,
                "time_diff": p.time_diff,
                "last_3f": p.last_3f,
                "weight_carried": p.weight_carried,
                "jockey_name": p.jockey_name,
                "odds": p.odds,
                "popularity": p.popularity,
                "margin": p.margin,
                "race_pace": p.race_pace,
                "running_style": p.running_style,
            }
            for p in performances
        ],
    })
