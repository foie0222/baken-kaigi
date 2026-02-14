"""購入APIハンドラー."""
import logging
import math
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

MIN_RACE_NUMBER = 1
MAX_RACE_NUMBER = 12

from src.api.auth import AuthenticationError, require_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.request import get_body, get_path_parameter
from src.api.response import (
    bad_request_response,
    forbidden_response,
    internal_error_response,
    not_found_response,
    success_response,
    unauthorized_response,
)
from src.application.use_cases.get_purchase_history import GetPurchaseHistoryUseCase
from src.application.use_cases.submit_purchase import (
    CartNotFoundError,
    CredentialsNotFoundError,
    IpatSubmissionError,
    PurchaseValidationError,
    SubmitPurchaseUseCase,
)
from src.domain.entities import Cart
from src.domain.enums import BetType
from src.domain.identifiers import CartId, PurchaseId, RaceId, UserId
from src.domain.ports import IpatGatewayError
from src.domain.value_objects import BetSelection, HorseNumbers, Money


def _expand_nagashi(item: dict) -> list[BetSelection]:
    """流し形式の買い目を個別のBetSelectionに展開する.

    軸馬（先頭）と各相手馬のペアに分割する。
    例: ワイド [1, 8, 14] → [1,8], [1,14] の2点
    """
    bet_type: BetType = item["bet_type"]
    horse_numbers: list[int] = item["horse_numbers"]
    amount: int = item["amount"]
    required = bet_type.get_required_count()

    if len(horse_numbers) <= required:
        return [
            BetSelection(
                bet_type=bet_type,
                horse_numbers=HorseNumbers.from_list(horse_numbers),
                amount=Money(amount),
            )
        ]

    axis = horse_numbers[0]
    partners = horse_numbers[1:]
    per_amount = amount // len(partners)

    return [
        BetSelection(
            bet_type=bet_type,
            horse_numbers=HorseNumbers.from_list([axis, partner]),
            amount=Money(per_amount),
        )
        for partner in partners
    ]


def submit_purchase_handler(event: dict, context: Any) -> dict:
    """購入を実行する.

    POST /purchases
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    cart_id = body.get("cart_id")
    race_date = body.get("race_date")
    course_code = body.get("course_code")
    race_number = body.get("race_number")

    if not cart_id:
        return bad_request_response("cart_id is required", event=event)
    if not isinstance(cart_id, str):
        return bad_request_response("cart_id must be a string", event=event)
    if not race_date:
        return bad_request_response("race_date is required", event=event)
    if not isinstance(race_date, str):
        return bad_request_response("race_date must be a string", event=event)
    if not course_code:
        return bad_request_response("course_code is required", event=event)
    if not isinstance(course_code, str):
        return bad_request_response("course_code must be a string", event=event)
    if race_number is None:
        return bad_request_response("race_number is required", event=event)
    if isinstance(race_number, bool) or not isinstance(race_number, (int, float)):
        return bad_request_response(
            f"race_number must be an integer between {MIN_RACE_NUMBER} and {MAX_RACE_NUMBER}",
            event=event,
        )
    if isinstance(race_number, float):
        if not math.isfinite(race_number):
            return bad_request_response("race_number must be a finite number", event=event)
        if race_number != int(race_number):
            return bad_request_response("race_number must be a whole number", event=event)
        race_number = int(race_number)
    if race_number < MIN_RACE_NUMBER or race_number > MAX_RACE_NUMBER:
        return bad_request_response(
            f"race_number must be between {MIN_RACE_NUMBER} and {MAX_RACE_NUMBER}",
            event=event,
        )

    # フロントエンドから送信されたカートアイテムのバリデーションとDynamoDB同期
    items = body.get("items")
    if items is None:
        items = []
    elif not isinstance(items, list):
        return bad_request_response("items must be a list", event=event)

    normalized_items: list[dict[str, Any]] = []
    for index, item_data in enumerate(items):
        if not isinstance(item_data, dict):
            return bad_request_response(f"items[{index}] must be an object", event=event)

        try:
            race_id_raw = item_data["race_id"]
            race_name_raw = item_data["race_name"]
            bet_type_raw = item_data["bet_type"]
            horse_numbers_raw = item_data["horse_numbers"]
            amount_raw = item_data["amount"]
        except KeyError as e:
            return bad_request_response(
                f"items[{index}] is missing required field '{e.args[0]}'",
                event=event,
            )

        if not isinstance(race_id_raw, str):
            return bad_request_response(f"items[{index}].race_id must be a string", event=event)
        if not isinstance(race_name_raw, str):
            return bad_request_response(f"items[{index}].race_name must be a string", event=event)
        if not isinstance(bet_type_raw, str):
            return bad_request_response(f"items[{index}].bet_type must be a string", event=event)

        try:
            bet_type = BetType(bet_type_raw.lower())
        except ValueError:
            return bad_request_response(f"items[{index}].bet_type is invalid", event=event)

        if not isinstance(horse_numbers_raw, list):
            return bad_request_response(f"items[{index}].horse_numbers must be a list", event=event)
        try:
            horse_numbers_list = [int(n) for n in horse_numbers_raw]
        except (TypeError, ValueError):
            return bad_request_response(
                f"items[{index}].horse_numbers must be a list of integers",
                event=event,
            )

        if isinstance(amount_raw, bool) or not isinstance(amount_raw, (int, float)):
            return bad_request_response(f"items[{index}].amount must be a number", event=event)
        if isinstance(amount_raw, float):
            if not math.isfinite(amount_raw):
                return bad_request_response(f"items[{index}].amount must be a finite number", event=event)
            if amount_raw != int(amount_raw):
                return bad_request_response(f"items[{index}].amount must be a whole number", event=event)
            amount_value = int(amount_raw)
        else:
            amount_value = int(amount_raw)

        normalized_items.append({
            "race_id": race_id_raw,
            "race_name": race_name_raw,
            "bet_type": bet_type,
            "horse_numbers": horse_numbers_list,
            "amount": amount_value,
        })

    cart_repository = Dependencies.get_cart_repository()
    if normalized_items and cart_repository.find_by_id(CartId(cart_id)) is None:
        now = datetime.now(timezone.utc)
        cart = Cart(
            cart_id=CartId(cart_id),
            user_id=UserId(user_id.value),
            created_at=now,
            updated_at=now,
        )
        try:
            for item in normalized_items:
                expanded = _expand_nagashi(item)
                for sel in expanded:
                    cart.add_item(
                        race_id=RaceId(item["race_id"]),
                        race_name=item["race_name"],
                        bet_selection=sel,
                    )
        except ValueError as e:
            return bad_request_response(str(e), event=event)
        cart_repository.save(cart)

    use_case = SubmitPurchaseUseCase(
        cart_repository=cart_repository,
        purchase_order_repository=Dependencies.get_purchase_order_repository(),
        ipat_gateway=Dependencies.get_ipat_gateway(),
        credentials_provider=Dependencies.get_credentials_provider(),
        spending_limit_provider=Dependencies.get_spending_limit_provider(),
    )

    try:
        order = use_case.execute(
            user_id=user_id.value,
            cart_id=cart_id,
            race_date=race_date,
            course_code=course_code,
            race_number=race_number,
        )
    except CartNotFoundError:
        return not_found_response("Cart", event=event)
    except CredentialsNotFoundError:
        return bad_request_response("IPAT credentials not configured", event=event)
    except PurchaseValidationError as e:
        return bad_request_response(str(e), event=event)
    except IpatSubmissionError as e:
        logger.exception("IpatSubmissionError: %s", e)
        return internal_error_response(str(e), event=event)
    except IpatGatewayError as e:
        logger.exception("IpatGatewayError: %s", e)
        return internal_error_response("IPAT通信エラーが発生しました", event=event)

    return success_response(
        {
            "purchase_id": str(order.id.value),
            "status": order.status.value,
            "total_amount": order.total_amount.value,
            "created_at": order.created_at.isoformat(),
        },
        status_code=201,
        event=event,
    )


def get_purchase_history_handler(event: dict, context: Any) -> dict:
    """購入履歴を取得する.

    GET /purchases
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    use_case = GetPurchaseHistoryUseCase(
        purchase_order_repository=Dependencies.get_purchase_order_repository(),
    )
    orders = use_case.execute(user_id.value)

    return success_response([
        {
            "purchase_id": str(order.id.value),
            "status": order.status.value,
            "total_amount": order.total_amount.value,
            "bet_line_count": len(order.bet_lines),
            "error_message": order.error_message,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        }
        for order in orders
    ], event=event)


def get_purchase_detail_handler(event: dict, context: Any) -> dict:
    """購入詳細を取得する.

    GET /purchases/{purchase_id}
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    purchase_id_str = get_path_parameter(event, "purchase_id")
    if not purchase_id_str:
        return bad_request_response("purchase_id is required", event=event)

    repo = Dependencies.get_purchase_order_repository()
    order = repo.find_by_id(PurchaseId(purchase_id_str))

    if order is None:
        return not_found_response("Purchase order", event=event)

    if order.user_id != user_id:
        return forbidden_response(event=event)

    return success_response({
        "purchase_id": str(order.id.value),
        "user_id": str(order.user_id.value),
        "cart_id": str(order.cart_id.value),
        "status": order.status.value,
        "total_amount": order.total_amount.value,
        "bet_lines": [
            {
                "opdt": line.opdt,
                "venue_code": line.venue_code.value,
                "race_number": line.race_number,
                "bet_type": line.bet_type.value,
                "number": line.number,
                "amount": line.amount,
            }
            for line in order.bet_lines
        ],
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "error_message": order.error_message,
    }, event=event)
