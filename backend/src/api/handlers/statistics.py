"""統計API ハンドラー."""
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_query_parameter
from src.api.response import bad_request_response, not_found_response, success_response


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


def get_past_race_stats(event: dict, context: Any) -> dict:
    """過去レース統計を取得する.

    GET /statistics/past-races?track_code=1&distance=1600&grade_code=G3&limit=100

    Query Parameters:
        track_code: トラックコード（1:芝, 2:ダート, 3:障害）（必須）
        distance: 距離（メートル）（必須）
        grade_code: グレードコード（省略可）
        limit: 集計対象レース数（デフォルト100、最大500）

    Returns:
        過去レース統計データ
    """
    track_code = get_query_parameter(event, "track_code")
    if not track_code:
        return bad_request_response("track_code is required")

    distance_str = get_query_parameter(event, "distance")
    if not distance_str:
        return bad_request_response("distance is required")

    try:
        distance = int(distance_str)
    except ValueError:
        return bad_request_response("Invalid distance format")

    grade_code = get_query_parameter(event, "grade_code")
    limit_str = get_query_parameter(event, "limit")

    limit = 100
    if limit_str:
        try:
            limit = int(limit_str)
            if limit < 10 or limit > 500:
                return bad_request_response("limit must be between 10 and 500")
        except ValueError:
            return bad_request_response("Invalid limit format")

    # track_codeを track_type に変換
    track_type_map = {"1": "芝", "2": "ダート", "3": "障害"}
    track_type = track_type_map.get(track_code, "芝")

    provider = Dependencies.get_race_data_provider()
    result = provider.get_past_race_stats(
        track_type=track_type,
        distance=distance,
        grade_class=grade_code,
        limit=limit,
    )

    if result is None:
        return not_found_response("Past race statistics")

    # レスポンス構築
    response = {
        "total_races": result.total_races,
        "popularity_stats": [
            {
                "popularity": s.popularity,
                "total_runs": s.total_runs,
                "wins": s.wins,
                "places": s.places,
                "win_rate": s.win_rate,
                "place_rate": s.place_rate,
            }
            for s in result.popularity_stats
        ],
        "avg_win_payout": result.avg_win_payout,
        "avg_place_payout": result.avg_place_payout,
        "conditions": {
            "track_type": result.track_type,
            "distance": result.distance,
            "grade_class": result.grade_class,
        },
    }

    return success_response(response)


def get_jockey_course_stats(event: dict, context: Any) -> dict:
    """騎手のコース別成績を取得する.

    GET /statistics/jockey-course?jockey_id=00001&track_code=1&distance=1600

    Query Parameters:
        jockey_id: 騎手コード（必須）
        track_code: トラックコード（1:芝, 2:ダート, 3:障害）（必須）
        distance: 距離（メートル）（必須）
        keibajo_code: 競馬場コード（01-10、省略可）
        limit: 集計対象レース数（デフォルト100）

    Returns:
        騎手コース別成績データ
    """
    jockey_id = get_query_parameter(event, "jockey_id")
    if not jockey_id:
        return bad_request_response("jockey_id is required")

    track_code = get_query_parameter(event, "track_code")
    if not track_code:
        return bad_request_response("track_code is required")

    distance_str = get_query_parameter(event, "distance")
    if not distance_str:
        return bad_request_response("distance is required")

    try:
        distance = int(distance_str)
    except ValueError:
        return bad_request_response("Invalid distance format")

    keibajo_code = get_query_parameter(event, "keibajo_code")

    # 競馬場名に変換
    keibajo_map = {
        "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
        "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉",
    }
    venue = keibajo_map.get(keibajo_code) if keibajo_code else None

    # track_codeを track_type に変換
    track_type_map = {"1": "芝", "2": "ダート", "3": "障害"}
    track_type = track_type_map.get(track_code, "芝")

    # course 文字列を構築（例: "芝1600m"）
    course = f"{track_type}{distance}m"
    if venue:
        course = f"{venue}{course}"

    provider = Dependencies.get_race_data_provider()
    result = provider.get_jockey_stats(jockey_id=jockey_id, course=course)

    if result is None:
        return not_found_response("Jockey course statistics")

    response = {
        "jockey_id": result.jockey_id,
        "jockey_name": result.jockey_name,
        "total_rides": result.total_races,
        "wins": result.wins,
        "places": int(result.total_races * result.place_rate / 100) if result.total_races > 0 else 0,
        "win_rate": result.win_rate,
        "place_rate": result.place_rate,
        "conditions": {
            "track_type": track_type,
            "distance": distance,
            "venue": venue,
        },
    }

    return success_response(response)


def get_popularity_payout_stats(event: dict, context: Any) -> dict:
    """人気別配当統計を取得する.

    GET /statistics/popularity-payout?track_code=1&distance=1600&popularity=1

    Query Parameters:
        track_code: トラックコード（1:芝, 2:ダート, 3:障害）（必須）
        distance: 距離（メートル）（必須）
        popularity: 人気順（1-18）（必須）
        limit: 集計対象レース数（デフォルト100）

    Returns:
        人気別配当統計データ
    """
    track_code = get_query_parameter(event, "track_code")
    if not track_code:
        return bad_request_response("track_code is required")

    distance_str = get_query_parameter(event, "distance")
    if not distance_str:
        return bad_request_response("distance is required")

    try:
        distance = int(distance_str)
    except ValueError:
        return bad_request_response("Invalid distance format")

    popularity_str = get_query_parameter(event, "popularity")
    if not popularity_str:
        return bad_request_response("popularity is required")

    try:
        popularity = int(popularity_str)
        if popularity < 1 or popularity > 18:
            return bad_request_response("popularity must be between 1 and 18")
    except ValueError:
        return bad_request_response("Invalid popularity format")

    limit_str = get_query_parameter(event, "limit")
    limit = 100
    if limit_str:
        try:
            limit = int(limit_str)
            if limit < 10 or limit > 500:
                return bad_request_response("limit must be between 10 and 500")
        except ValueError:
            return bad_request_response("Invalid limit format")

    # track_codeを track_type に変換
    track_type_map = {"1": "芝", "2": "ダート", "3": "障害"}
    track_type = track_type_map.get(track_code, "芝")

    # 過去レース統計から人気別データを取得
    provider = Dependencies.get_race_data_provider()
    result = provider.get_past_race_stats(
        track_type=track_type,
        distance=distance,
        grade_class=None,
        limit=limit,
    )

    if result is None:
        return not_found_response("Popularity payout statistics")

    # 指定人気の統計を抽出
    target_stats = next(
        (s for s in result.popularity_stats if s.popularity == popularity),
        None
    )

    if target_stats is None:
        return not_found_response(f"Statistics for popularity {popularity}")

    # 回収率を推定（平均配当 * 勝率 / 100）
    estimated_roi_win = 0.0
    estimated_roi_place = 0.0

    if result.avg_win_payout and target_stats.win_rate > 0:
        estimated_roi_win = (result.avg_win_payout * target_stats.win_rate) / 100

    if result.avg_place_payout and target_stats.place_rate > 0:
        estimated_roi_place = (result.avg_place_payout * target_stats.place_rate) / 100

    response = {
        "popularity": popularity,
        "total_races": result.total_races,
        "win_count": target_stats.wins,
        "avg_win_payout": result.avg_win_payout,
        "avg_place_payout": result.avg_place_payout,
        "estimated_roi_win": estimated_roi_win,
        "estimated_roi_place": estimated_roi_place,
    }

    return success_response(response)
