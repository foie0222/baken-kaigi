"""購入APIハンドラー."""
import logging
from typing import Any

logger = logging.getLogger(__name__)

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
from src.domain.identifiers import PurchaseId
from src.domain.ports import IpatGatewayError


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
    if not race_date:
        return bad_request_response("race_date is required", event=event)
    if not course_code:
        return bad_request_response("course_code is required", event=event)
    if race_number is None:
        return bad_request_response("race_number is required", event=event)

    use_case = SubmitPurchaseUseCase(
        cart_repository=Dependencies.get_cart_repository(),
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
