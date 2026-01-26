"""統計API ハンドラー."""
import logging
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_query_parameter
from src.api.response import bad_request_response, not_found_response, success_response

logger = logging.getLogger(__name__)


def get_gate_position_stats(event: dict, context: Any) -> dict:
    """枠順別成績統計を取得する.

    GET /statistics/gate-position?venue=阪神&track_type=芝&distance=1600

    Query Parameters:
        venue: 競馬場（必須）
        track_type: 芝/ダート/障害
        distance: 距離（メートル）
        track_condition: 馬場状態（良/稍/重/不）
        limit: 集計対象レース数（デフォルト100）

    Returns:
        枠順別成績統計データ
    """
    # パラメータ取得
    venue = get_query_parameter(event, "venue")
    if not venue:
        return bad_request_response("venue is required")

    track_type = get_query_parameter(event, "track_type")
    distance_str = get_query_parameter(event, "distance")
    track_condition = get_query_parameter(event, "track_condition")
    limit_str = get_query_parameter(event, "limit")

    distance: int | None = None
    if distance_str:
        try:
            distance = int(distance_str)
        except ValueError:
            return bad_request_response("Invalid distance format")

    limit = 100
    if limit_str:
        try:
            limit = int(limit_str)
            if limit < 1 or limit > 500:
                return bad_request_response("limit must be between 1 and 500")
        except ValueError:
            return bad_request_response("Invalid limit format")

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    result = provider.get_gate_position_stats(
        venue=venue,
        track_type=track_type,
        distance=distance,
        track_condition=track_condition,
        limit=limit,
    )

    if result is None:
        return not_found_response("Gate position statistics")

    # レスポンス構築
    response = {
        "conditions": {
            "venue": result.conditions.venue,
            "track_type": result.conditions.track_type,
            "distance": result.conditions.distance,
            "track_condition": result.conditions.track_condition,
        },
        "total_races": result.total_races,
        "by_gate": [
            {
                "gate": g.gate,
                "gate_range": g.gate_range,
                "starts": g.starts,
                "wins": g.wins,
                "places": g.places,
                "win_rate": g.win_rate,
                "place_rate": g.place_rate,
                "avg_finish": g.avg_finish,
            }
            for g in result.by_gate
        ],
        "by_horse_number": [
            {
                "horse_number": h.horse_number,
                "starts": h.starts,
                "wins": h.wins,
                "win_rate": h.win_rate,
            }
            for h in result.by_horse_number
        ],
        "analysis": {
            "favorable_gates": result.analysis.favorable_gates,
            "unfavorable_gates": result.analysis.unfavorable_gates,
            "comment": result.analysis.comment,
        },
    }

    return success_response(response)
