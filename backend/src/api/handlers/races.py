"""レースAPI ハンドラー."""
from datetime import date, datetime
from typing import Any

from src.api.dependencies import Dependencies
from src.api.request import get_path_parameter, get_query_parameter
from src.api.response import bad_request_response, not_found_response, success_response
from src.application.use_cases import GetRaceDetailUseCase, GetRaceListUseCase
from src.domain.identifiers import RaceId


def get_races(event: dict, context: Any) -> dict:
    """レース一覧を取得する.

    GET /races?date=2024-06-01&venue=東京

    Query Parameters:
        date: 日付（必須、YYYY-MM-DD形式）
        venue: 開催場（オプション）

    Returns:
        レース一覧
    """
    # パラメータ取得
    date_str = get_query_parameter(event, "date")
    if not date_str:
        return bad_request_response("date parameter is required")

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return bad_request_response("Invalid date format. Use YYYY-MM-DD")

    venue = get_query_parameter(event, "venue")

    # ユースケース実行
    provider = Dependencies.get_race_data_provider()
    use_case = GetRaceListUseCase(provider)
    result = use_case.execute(target_date, venue)

    # レスポンス構築
    races = [
        {
            "race_id": r.race_id,
            "race_name": r.race_name,
            "race_number": r.race_number,
            "venue": r.venue,
            "start_time": r.start_time.isoformat(),
            "betting_deadline": r.betting_deadline.isoformat(),
            "track_condition": r.track_condition,
            "track_type": r.track_type,
            "distance": r.distance,
            "horse_count": r.horse_count,
        }
        for r in result.races
    ]

    return success_response(
        {
            "races": races,
            "venues": result.venues,
            "target_date": result.target_date.isoformat(),
        }
    )


def get_race_detail(event: dict, context: Any) -> dict:
    """レース詳細を取得する.

    GET /races/{race_id}

    Path Parameters:
        race_id: レースID

    Returns:
        レース詳細と出走馬一覧
    """
    race_id_str = get_path_parameter(event, "race_id")
    if not race_id_str:
        return bad_request_response("race_id is required")

    # ユースケース実行
    provider = Dependencies.get_race_data_provider()
    use_case = GetRaceDetailUseCase(provider)
    result = use_case.execute(RaceId(race_id_str))

    if result is None:
        return not_found_response("Race")

    # レスポンス構築
    race = {
        "race_id": result.race.race_id,
        "race_name": result.race.race_name,
        "race_number": result.race.race_number,
        "venue": result.race.venue,
        "start_time": result.race.start_time.isoformat(),
        "betting_deadline": result.race.betting_deadline.isoformat(),
        "track_condition": result.race.track_condition,
        "track_type": result.race.track_type,
        "distance": result.race.distance,
        "horse_count": result.race.horse_count,
    }

    runners = [
        {
            "horse_number": r.horse_number,
            "waku_ban": r.waku_ban,
            "horse_name": r.horse_name,
            "jockey_name": r.jockey_name,
            "odds": r.odds,
            "popularity": r.popularity,
        }
        for r in result.runners
    ]

    return success_response({"race": race, "runners": runners})
