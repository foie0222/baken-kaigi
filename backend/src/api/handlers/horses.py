"""馬API ハンドラー."""
import logging
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_path_parameter, get_query_parameter
from src.api.response import bad_request_response, not_found_response, success_response

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
        return bad_request_response("horse_id is required", event=event)

    # パラメータ取得
    limit_str = get_query_parameter(event, "limit")
    track_type = get_query_parameter(event, "track_type")

    # limitのバリデーション
    limit = 5
    if limit_str:
        try:
            limit = int(limit_str)
            if limit < 1 or limit > 20:
                return bad_request_response("limit must be between 1 and 20", event=event)
        except ValueError:
            return bad_request_response("limit must be a valid integer", event=event)

    # track_typeのバリデーション
    valid_track_types = ["芝", "ダート", "障害"]
    if track_type and track_type not in valid_track_types:
        return bad_request_response(
            f"track_type must be one of: {', '.join(valid_track_types)}",
            event=event,
        )

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    performances = provider.get_horse_performances(horse_id, limit, track_type)

    # 馬名は最初のレコードから取得（全レコード同じはず）
    horse_name = performances[0].horse_name if performances else None

    return success_response({
        "horse_id": horse_id,
        "horse_name": horse_name,
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
    }, event=event)


def get_horse_training(event: dict, context: Any) -> dict:
    """馬の調教データを取得する.

    GET /horses/{horse_id}/training

    Path Parameters:
        horse_id: 馬コード

    Query Parameters:
        limit: 取得件数（デフォルト: 5、最大: 10）
        days: 直近N日分（デフォルト: 30）

    Returns:
        馬の調教データとサマリー
    """
    horse_id = get_path_parameter(event, "horse_id")
    if not horse_id:
        return bad_request_response("horse_id is required", event=event)

    # パラメータ取得
    limit_str = get_query_parameter(event, "limit")
    days_str = get_query_parameter(event, "days")

    # limitのバリデーション
    limit = 5
    if limit_str:
        try:
            limit = int(limit_str)
            if limit < 1 or limit > 10:
                return bad_request_response("limit must be between 1 and 10", event=event)
        except ValueError:
            return bad_request_response("limit must be a valid integer", event=event)

    # daysのバリデーション
    days = 30
    if days_str:
        try:
            days = int(days_str)
            if days < 1 or days > 365:
                return bad_request_response("days must be between 1 and 365", event=event)
        except ValueError:
            return bad_request_response("days must be a valid integer", event=event)

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    records, summary = provider.get_horse_training(horse_id, limit, days)

    # 馬名を取得（pedigreeから）
    pedigree = provider.get_pedigree(horse_id)
    horse_name = pedigree.horse_name if pedigree else None

    return success_response({
        "horse_id": horse_id,
        "horse_name": horse_name,
        "training_records": [
            {
                "date": r.date,
                "course": r.course,
                "course_condition": r.course_condition,
                "distance": r.distance,
                "time": r.time,
                "last_3f": r.last_3f,
                "last_1f": r.last_1f,
                "training_type": r.training_type,
                "partner_horse": r.partner_horse,
                "evaluation": r.evaluation,
                "comment": r.comment,
            }
            for r in records
        ],
        "training_summary": {
            "recent_trend": summary.recent_trend,
            "average_time": summary.average_time,
            "best_time": summary.best_time,
        } if summary else None,
    }, event=event)


def get_extended_pedigree(event: dict, context: Any) -> dict:
    """馬の拡張血統情報（3代血統）を取得する.

    GET /horses/{horse_id}/pedigree/extended

    Path Parameters:
        horse_id: 馬コード

    Returns:
        馬の拡張血統情報（父母の3代血統、インブリード情報、系統タイプ）
    """
    horse_id = get_path_parameter(event, "horse_id")
    if not horse_id:
        return bad_request_response("horse_id is required", event=event)

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    extended_pedigree = provider.get_extended_pedigree(horse_id)

    if not extended_pedigree:
        return not_found_response("Horse pedigree", event=event)

    return success_response({
        "horse_id": extended_pedigree.horse_id,
        "horse_name": extended_pedigree.horse_name,
        "sire": {
            "name": extended_pedigree.sire.name,
            "sire": extended_pedigree.sire.sire,
            "dam": extended_pedigree.sire.dam,
            "broodmare_sire": extended_pedigree.sire.broodmare_sire,
        } if extended_pedigree.sire else None,
        "dam": {
            "name": extended_pedigree.dam.name,
            "sire": extended_pedigree.dam.sire,
            "dam": extended_pedigree.dam.dam,
            "broodmare_sire": extended_pedigree.dam.broodmare_sire,
        } if extended_pedigree.dam else None,
        "inbreeding": [
            {
                "ancestor": i.ancestor,
                "pattern": i.pattern,
                "percentage": i.percentage,
            }
            for i in extended_pedigree.inbreeding
        ],
        "lineage_type": extended_pedigree.lineage_type,
    }, event=event)


def get_course_aptitude(event: dict, context: Any) -> dict:
    """馬のコース適性を取得する.

    GET /horses/{horse_id}/course-aptitude

    Path Parameters:
        horse_id: 馬コード

    Returns:
        馬のコース適性（競馬場別、コース種別、距離別、馬場状態別、枠番別、サマリー）
    """
    horse_id = get_path_parameter(event, "horse_id")
    if not horse_id:
        return bad_request_response("horse_id is required", event=event)

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    aptitude = provider.get_course_aptitude(horse_id)

    if not aptitude:
        return not_found_response("Horse course aptitude", event=event)

    return success_response({
        "horse_id": aptitude.horse_id,
        "horse_name": aptitude.horse_name,
        "by_venue": [
            {
                "venue": v.venue,
                "starts": v.starts,
                "wins": v.wins,
                "places": v.places,
                "win_rate": v.win_rate,
                "place_rate": v.place_rate,
            }
            for v in aptitude.by_venue
        ],
        "by_track_type": [
            {
                "track_type": t.track_type,
                "starts": t.starts,
                "wins": t.wins,
                "win_rate": t.win_rate,
            }
            for t in aptitude.by_track_type
        ],
        "by_distance": [
            {
                "distance_range": d.distance_range,
                "starts": d.starts,
                "wins": d.wins,
                "win_rate": d.win_rate,
                "best_time": d.best_time,
            }
            for d in aptitude.by_distance
        ],
        "by_track_condition": [
            {
                "condition": c.condition,
                "starts": c.starts,
                "wins": c.wins,
                "win_rate": c.win_rate,
            }
            for c in aptitude.by_track_condition
        ],
        "by_running_position": [
            {
                "position": p.position,
                "starts": p.starts,
                "wins": p.wins,
                "win_rate": p.win_rate,
            }
            for p in aptitude.by_running_position
        ],
        "aptitude_summary": {
            "best_venue": aptitude.aptitude_summary.best_venue,
            "best_distance": aptitude.aptitude_summary.best_distance,
            "preferred_condition": aptitude.aptitude_summary.preferred_condition,
            "preferred_position": aptitude.aptitude_summary.preferred_position,
        } if aptitude.aptitude_summary else None,
    }, event=event)
