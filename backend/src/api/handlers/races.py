"""レースAPI ハンドラー."""
import logging
from datetime import date, datetime
from typing import Any

from src.api.dependencies import Dependencies

logger = logging.getLogger(__name__)
from src.api.request import get_path_parameter, get_query_parameter
from src.api.response import bad_request_response, not_found_response, success_response
from src.application.use_cases import GetRaceDetailUseCase, GetRaceListUseCase
from src.domain.identifiers import RaceId


def get_race_dates(event: dict, context: Any) -> dict:
    """開催日一覧を取得する.

    GET /race-dates?from=2024-06-01&to=2024-06-30

    Query Parameters:
        from: 開始日（オプション、YYYY-MM-DD形式）
        to: 終了日（オプション、YYYY-MM-DD形式）

    Returns:
        開催日一覧
    """
    # パラメータ取得
    from_str = get_query_parameter(event, "from")
    to_str = get_query_parameter(event, "to")

    from_date: date | None = None
    to_date: date | None = None

    if from_str:
        try:
            from_date = datetime.strptime(from_str, "%Y-%m-%d").date()
        except ValueError:
            return bad_request_response("Invalid from date format. Use YYYY-MM-DD", event=event)

    if to_str:
        try:
            to_date = datetime.strptime(to_str, "%Y-%m-%d").date()
        except ValueError:
            return bad_request_response("Invalid to date format. Use YYYY-MM-DD", event=event)

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    dates = provider.get_race_dates(from_date, to_date)

    return success_response({
        "dates": [d.isoformat() for d in dates],
    }, event=event)


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
        return bad_request_response("date parameter is required", event=event)

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return bad_request_response("Invalid date format. Use YYYY-MM-DD", event=event)

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
            # 条件フィールド
            "grade_class": r.grade_class,
            "age_condition": r.age_condition,
            "is_obstacle": r.is_obstacle,
            # JRA出馬表URL生成用
            "kaisai_kai": r.kaisai_kai,
            "kaisai_nichime": r.kaisai_nichime,
        }
        for r in result.races
    ]

    return success_response(
        {
            "races": races,
            "venues": result.venues,
            "target_date": result.target_date.isoformat(),
        },
        event=event,
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
        return bad_request_response("race_id is required", event=event)

    # ユースケース実行
    provider = Dependencies.get_race_data_provider()
    use_case = GetRaceDetailUseCase(provider)
    race_id = RaceId(race_id_str)
    result = use_case.execute(race_id)

    if result is None:
        return not_found_response("Race", event=event)

    # JRAチェックサムを取得
    jra_checksum = None
    if result.race.kaisai_kai and result.race.kaisai_nichime:
        try:
            kaisai_nichime_int = int(result.race.kaisai_nichime)
            jra_checksum = provider.get_jra_checksum(
                venue_code=result.race.venue,
                kaisai_kai=result.race.kaisai_kai,
                kaisai_nichime=kaisai_nichime_int,
                race_number=result.race.race_number,
            )
        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to get JRA checksum for race %s: %s",
                race_id_str,
                e,
            )

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
        # 条件フィールド
        "grade_class": result.race.grade_class,
        "age_condition": result.race.age_condition,
        "is_obstacle": result.race.is_obstacle,
        # JRA出馬表URL生成用
        "kaisai_kai": result.race.kaisai_kai,
        "kaisai_nichime": result.race.kaisai_nichime,
        "jra_checksum": jra_checksum,
    }

    # 馬体重情報を取得
    race_weights = provider.get_race_weights(race_id)

    runners = []
    for r in result.runners:
        runner_dict = {
            "horse_number": r.horse_number,
            "waku_ban": r.waku_ban,
            "horse_name": r.horse_name,
            "jockey_name": r.jockey_name,
            "odds": r.odds,
            "popularity": r.popularity,
        }
        # 馬体重を追加（存在する場合）
        weight_data = race_weights.get(r.horse_number)
        if weight_data:
            runner_dict["weight"] = weight_data.weight
            runner_dict["weight_diff"] = weight_data.weight_diff
        runners.append(runner_dict)

    return success_response({"race": race, "runners": runners}, event=event)


def get_odds_history(event: dict, context: Any) -> dict:
    """レースのオッズ履歴を取得する.

    GET /races/{race_id}/odds-history

    Path Parameters:
        race_id: レースID

    Returns:
        オッズ履歴データ
    """
    race_id_str = get_path_parameter(event, "race_id")
    if not race_id_str:
        return bad_request_response("race_id is required", event=event)

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    race_id = RaceId(race_id_str)
    result = provider.get_odds_history(race_id)

    if result is None:
        return not_found_response("Race", event=event)

    # レスポンス構築
    response = {
        "race_id": result.race_id,
        "odds_history": [
            {
                "timestamp": ts.timestamp,
                "odds": [
                    {
                        "horse_number": o.horse_number,
                        "win_odds": o.win_odds,
                        "place_odds_min": o.place_odds_min,
                        "place_odds_max": o.place_odds_max,
                        "popularity": o.popularity,
                    }
                    for o in ts.odds
                ],
            }
            for ts in result.odds_history
        ],
        "odds_movement": [
            {
                "horse_number": m.horse_number,
                "initial_odds": m.initial_odds,
                "final_odds": m.final_odds,
                "change_rate": m.change_rate,
                "trend": m.trend,
            }
            for m in result.odds_movement
        ],
        "notable_movements": [
            {
                "horse_number": n.horse_number,
                "description": n.description,
            }
            for n in result.notable_movements
        ],
    }

    return success_response(response, event=event)


def get_running_styles(event: dict, context: Any) -> dict:
    """レースの出走馬の脚質データを取得する.

    GET /races/{race_id}/running-styles

    Path Parameters:
        race_id: レースID

    Returns:
        脚質データのリスト
    """
    race_id_str = get_path_parameter(event, "race_id")
    if not race_id_str:
        return bad_request_response("race_id is required", event=event)

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    race_id = RaceId(race_id_str)
    result = provider.get_running_styles(race_id)

    # レスポンス構築
    response = [
        {
            "horse_number": s.horse_number,
            "horse_name": s.horse_name,
            "running_style": s.running_style,
            "running_style_tendency": s.running_style_tendency,
        }
        for s in result
    ]

    return success_response(response, event=event)


def get_race_results(event: dict, context: Any) -> dict:
    """レース結果・払戻金を取得する.

    GET /races/{race_id}/results

    Path Parameters:
        race_id: レースID

    Returns:
        レース結果（着順、タイム）と払戻金情報
    """
    race_id_str = get_path_parameter(event, "race_id")
    if not race_id_str:
        return bad_request_response("race_id is required", event=event)

    # プロバイダから取得
    provider = Dependencies.get_race_data_provider()
    race_id = RaceId(race_id_str)
    result = provider.get_race_results(race_id)

    if result is None:
        return not_found_response("Race results", event=event)

    # レスポンス構築
    response = {
        "race_id": result.race_id,
        "race_name": result.race_name,
        "race_date": result.race_date,
        "venue": result.venue,
        "is_finalized": result.is_finalized,
        "results": [
            {
                "horse_number": r.horse_number,
                "horse_name": r.horse_name,
                "finish_position": r.finish_position,
                "time": r.time,
                "margin": r.margin,
                "last_3f": r.last_3f,
                "popularity": r.popularity,
                "odds": r.odds,
                "jockey_name": r.jockey_name,
            }
            for r in result.results
        ],
        "payouts": [
            {
                "bet_type": p.bet_type,
                "combination": p.combination,
                "payout": p.payout,
                "popularity": p.popularity,
            }
            for p in result.payouts
        ],
    }

    return success_response(response, event=event)


def get_bet_odds(event: dict, context: Any) -> dict:
    """指定した買い目のオッズを取得する.

    GET /races/{race_id}/bet-odds?bet_type=win&horses=3

    Path Parameters:
        race_id: レースID

    Query Parameters:
        bet_type: 券種（win, place, quinella, exacta, trio, trifecta, quinella_place）
        horses: 馬番（カンマ区切り、例: "3" or "3,7" or "3,7,11"）

    Returns:
        オッズデータ
    """
    race_id_str = get_path_parameter(event, "race_id")
    if not race_id_str:
        return bad_request_response("race_id is required", event=event)

    bet_type = get_query_parameter(event, "bet_type")
    horses_str = get_query_parameter(event, "horses")
    if not bet_type or not horses_str:
        return bad_request_response("bet_type and horses are required", event=event)

    valid_bet_types = {"win", "place", "quinella", "quinella_place", "wide", "exacta", "trio", "trifecta"}
    if bet_type not in valid_bet_types:
        return bad_request_response(f"Invalid bet_type: {bet_type}", event=event)

    try:
        horse_numbers = [int(h.strip()) for h in horses_str.split(",") if h.strip()]
        if not horse_numbers:
            return bad_request_response("horses must contain at least one horse number", event=event)
    except ValueError:
        return bad_request_response("horses must contain valid integers", event=event)

    provider = Dependencies.get_race_data_provider()
    result = provider.get_bet_odds(RaceId(race_id_str), bet_type, horse_numbers)

    if result is None:
        return not_found_response("オッズデータが見つかりません", event=event)

    return success_response({
        "bet_type": result.bet_type,
        "horse_numbers": result.horse_numbers,
        "odds": result.odds,
        "odds_min": result.odds_min,
        "odds_max": result.odds_max,
    }, event=event)
