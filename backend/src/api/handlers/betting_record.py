"""投票記録APIハンドラー."""
import math
from typing import Any

from src.api.auth import AuthenticationError, require_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.request import get_body, get_path_parameter, get_query_parameter
from src.api.response import (
    bad_request_response,
    not_found_response,
    success_response,
    unauthorized_response,
)
from src.application.use_cases.create_betting_record import CreateBettingRecordUseCase
from src.application.use_cases.get_betting_records import GetBettingRecordsUseCase
from src.application.use_cases.get_betting_summary import GetBettingSummaryUseCase
from src.application.use_cases.settle_betting_record import (
    BettingRecordNotFoundError,
    SettleBettingRecordUseCase,
)


def betting_record_handler(event: dict, context: Any) -> dict:
    """投票記録APIルーティングハンドラー.

    リクエストのresourceとhttpMethodに基づいて適切なハンドラーに振り分ける。
    """
    resource = event.get("resource", "")
    method = event.get("httpMethod", "")

    if resource == "/betting-records" and method == "POST":
        return create_betting_record_handler(event, context)
    if resource == "/betting-records" and method == "GET":
        return get_betting_records_handler(event, context)
    if resource == "/betting-records/summary" and method == "GET":
        return get_betting_summary_handler(event, context)
    if resource == "/betting-records/{record_id}/settle" and method == "PUT":
        return settle_betting_record_handler(event, context)

    return bad_request_response("Unknown route", event=event)


def create_betting_record_handler(event: dict, context: Any) -> dict:
    """投票記録を作成する.

    POST /betting-records
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    race_id = body.get("race_id")
    race_name = body.get("race_name")
    race_date = body.get("race_date")
    venue = body.get("venue")
    bet_type = body.get("bet_type")
    horse_numbers = body.get("horse_numbers")
    amount = body.get("amount")

    if not race_id:
        return bad_request_response("race_id is required", event=event)
    if not isinstance(race_id, str):
        return bad_request_response("race_id must be a string", event=event)
    if not race_name:
        return bad_request_response("race_name is required", event=event)
    if not isinstance(race_name, str):
        return bad_request_response("race_name must be a string", event=event)
    if not race_date:
        return bad_request_response("race_date is required", event=event)
    if not isinstance(race_date, str):
        return bad_request_response("race_date must be a string", event=event)
    if not venue:
        return bad_request_response("venue is required", event=event)
    if not isinstance(venue, str):
        return bad_request_response("venue must be a string", event=event)
    if not bet_type:
        return bad_request_response("bet_type is required", event=event)
    if not isinstance(bet_type, str):
        return bad_request_response("bet_type must be a string", event=event)
    if not horse_numbers:
        return bad_request_response("horse_numbers is required", event=event)
    if not isinstance(horse_numbers, list):
        return bad_request_response("horse_numbers must be a list", event=event)
    if not all(isinstance(n, int) and not isinstance(n, bool) for n in horse_numbers):
        return bad_request_response("horse_numbers must be a list of integers", event=event)
    if amount is None:
        return bad_request_response("amount is required", event=event)
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        return bad_request_response("amount must be a positive number", event=event)
    if isinstance(amount, float):
        if not math.isfinite(amount):
            return bad_request_response("amount must be a finite number", event=event)
        if amount != int(amount):
            return bad_request_response("amount must be a whole number", event=event)
        amount = int(amount)
    if amount <= 0:
        return bad_request_response("amount must be a positive number", event=event)

    use_case = CreateBettingRecordUseCase(
        betting_record_repository=Dependencies.get_betting_record_repository(),
    )

    try:
        record = use_case.execute(
            user_id=user_id.value,
            race_id=race_id,
            race_name=race_name,
            race_date=race_date,
            venue=venue,
            bet_type=bet_type,
            horse_numbers=horse_numbers,
            amount=amount,
        )
    except (ValueError, KeyError) as e:
        return bad_request_response(str(e), event=event)

    return success_response(
        {
            "record_id": record.record_id.value,
            "race_id": record.race_id.value,
            "race_name": record.race_name,
            "race_date": record.race_date.isoformat(),
            "venue": record.venue,
            "bet_type": record.bet_type.value,
            "horse_numbers": record.horse_numbers.to_list(),
            "amount": record.amount.value,
            "payout": record.payout.value,
            "profit": record.profit,
            "status": record.status.value,
            "created_at": record.created_at.isoformat(),
            "settled_at": None,
        },
        status_code=201,
        event=event,
    )


def get_betting_records_handler(event: dict, context: Any) -> dict:
    """投票記録一覧を取得する.

    GET /betting-records
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    date_from = get_query_parameter(event, "date_from")
    date_to = get_query_parameter(event, "date_to")
    venue = get_query_parameter(event, "venue")
    bet_type = get_query_parameter(event, "bet_type")

    use_case = GetBettingRecordsUseCase(
        betting_record_repository=Dependencies.get_betting_record_repository(),
    )

    try:
        records = use_case.execute(
            user_id=user_id.value,
            date_from=date_from,
            date_to=date_to,
            venue=venue,
            bet_type=bet_type,
        )
    except (ValueError, KeyError) as e:
        return bad_request_response(str(e), event=event)

    return success_response([
        {
            "record_id": r.record_id.value,
            "race_id": r.race_id.value,
            "race_name": r.race_name,
            "race_date": r.race_date.isoformat(),
            "venue": r.venue,
            "bet_type": r.bet_type.value,
            "horse_numbers": r.horse_numbers.to_list(),
            "amount": r.amount.value,
            "payout": r.payout.value,
            "profit": r.profit,
            "status": r.status.value,
            "created_at": r.created_at.isoformat(),
            "settled_at": r.settled_at.isoformat() if r.settled_at else None,
        }
        for r in records
    ], event=event)


def get_betting_summary_handler(event: dict, context: Any) -> dict:
    """投票成績サマリーを取得する.

    GET /betting-records/summary
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    period = get_query_parameter(event, "period", default="all_time")

    use_case = GetBettingSummaryUseCase(
        betting_record_repository=Dependencies.get_betting_record_repository(),
    )

    summary = use_case.execute(user_id=user_id.value, period=period)

    return success_response({
        "total_investment": summary.total_investment.value,
        "total_payout": summary.total_payout.value,
        "net_profit": summary.net_profit,
        "win_rate": summary.win_rate,
        "record_count": summary.record_count,
        "roi": summary.roi,
    }, event=event)


def settle_betting_record_handler(event: dict, context: Any) -> dict:
    """投票記録を確定する.

    PUT /betting-records/{record_id}/settle
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    record_id = get_path_parameter(event, "record_id")
    if not record_id:
        return bad_request_response("record_id is required", event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    payout = body.get("payout")
    if payout is None:
        return bad_request_response("payout is required", event=event)
    if isinstance(payout, bool) or not isinstance(payout, (int, float)):
        return bad_request_response("payout must be a non-negative number", event=event)
    if isinstance(payout, float):
        if not math.isfinite(payout):
            return bad_request_response("payout must be a finite number", event=event)
        if payout != int(payout):
            return bad_request_response("payout must be a whole number", event=event)
        payout = int(payout)
    if payout < 0:
        return bad_request_response("payout must be a non-negative number", event=event)

    use_case = SettleBettingRecordUseCase(
        betting_record_repository=Dependencies.get_betting_record_repository(),
    )

    try:
        record = use_case.execute(
            user_id=user_id.value,
            record_id=record_id,
            payout=payout,
        )
    except BettingRecordNotFoundError:
        return not_found_response("Betting record", event=event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    return success_response({
        "record_id": record.record_id.value,
        "status": record.status.value,
        "payout": record.payout.value,
        "profit": record.profit,
        "settled_at": record.settled_at.isoformat() if record.settled_at else None,
    }, event=event)
