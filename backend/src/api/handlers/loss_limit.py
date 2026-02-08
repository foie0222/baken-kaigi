"""負け額限度額API ハンドラー."""
from typing import Any

from src.api.auth import AuthenticationError, require_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.request import get_body, get_query_parameter
from src.api.response import (
    bad_request_response,
    not_found_response,
    success_response,
    unauthorized_response,
)
from src.application.use_cases.check_loss_limit import CheckLossLimitUseCase
from src.application.use_cases.check_loss_limit import (
    UserNotFoundError as CheckUserNotFoundError,
)
from src.application.use_cases.get_loss_limit import GetLossLimitUseCase
from src.application.use_cases.get_loss_limit import (
    UserNotFoundError as GetUserNotFoundError,
)
from src.application.use_cases.set_loss_limit import (
    InvalidLossLimitAmountError,
    LossLimitAlreadySetError,
    SetLossLimitUseCase,
)
from src.application.use_cases.set_loss_limit import (
    UserNotFoundError as SetUserNotFoundError,
)
from src.application.use_cases.update_loss_limit import (
    LossLimitNotSetError,
    PendingChangeExistsError,
    UpdateLossLimitUseCase,
)
from src.application.use_cases.update_loss_limit import (
    InvalidLossLimitAmountError as UpdateInvalidAmountError,
)
from src.application.use_cases.update_loss_limit import (
    UserNotFoundError as UpdateUserNotFoundError,
)


def loss_limit_handler(event: dict, context: Any) -> dict:
    """負け額限度額APIルーティングハンドラー.

    リクエストのresourceとhttpMethodに基づいて適切なハンドラーに振り分ける。
    """
    resource = event.get("resource", "")
    method = event.get("httpMethod", "")

    if resource == "/users/loss-limit" and method == "GET":
        return get_loss_limit_handler(event, context)
    if resource == "/users/loss-limit" and method == "POST":
        return set_loss_limit_handler(event, context)
    if resource == "/users/loss-limit" and method == "PUT":
        return update_loss_limit_handler(event, context)
    if resource == "/users/loss-limit/check" and method == "GET":
        return check_loss_limit_handler(event, context)

    return bad_request_response("Unknown route", event=event)


def get_loss_limit_handler(event: dict, context: Any) -> dict:
    """負け額限度額を取得する.

    GET /users/loss-limit

    Returns:
        限度額情報
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    user_repo = Dependencies.get_user_repository()
    change_repo = Dependencies.get_loss_limit_change_repository()
    use_case = GetLossLimitUseCase(user_repo, change_repo)

    try:
        result = use_case.execute(user_id)
    except GetUserNotFoundError:
        return not_found_response("User", event=event)

    pending_change = None
    if result.pending_changes:
        c = result.pending_changes[0]
        pending_change = {
            "change_id": str(c.change_id),
            "change_type": c.change_type.value,
            "status": c.status.value,
            "current_limit": c.current_limit.value,
            "requested_limit": c.requested_limit.value,
            "effective_at": c.effective_at.isoformat(),
            "requested_at": c.requested_at.isoformat(),
        }

    return success_response(
        {
            "loss_limit": result.loss_limit.value if result.loss_limit else None,
            "total_loss_this_month": result.total_loss_this_month.value,
            "remaining_loss_limit": result.remaining_amount.value if result.remaining_amount else None,
            "pending_change": pending_change,
        },
        event=event,
    )


def set_loss_limit_handler(event: dict, context: Any) -> dict:
    """負け額限度額を設定する.

    POST /users/loss-limit

    Request Body:
        amount: 限度額（円）

    Returns:
        設定結果
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    if "amount" not in body:
        return bad_request_response("amount is required", event=event)

    amount = body["amount"]
    if isinstance(amount, bool) or not isinstance(amount, int):
        return bad_request_response("amount must be an integer", event=event)

    user_repo = Dependencies.get_user_repository()
    change_repo = Dependencies.get_loss_limit_change_repository()
    use_case = SetLossLimitUseCase(user_repo, change_repo)

    try:
        result = use_case.execute(user_id, amount)
    except SetUserNotFoundError:
        return not_found_response("User", event=event)
    except LossLimitAlreadySetError:
        return bad_request_response("Loss limit is already set", event=event)
    except InvalidLossLimitAmountError as e:
        return bad_request_response(str(e), event=event)

    return success_response(
        {"loss_limit": result.loss_limit.value},
        status_code=201,
        event=event,
    )


def update_loss_limit_handler(event: dict, context: Any) -> dict:
    """負け額限度額を変更する.

    PUT /users/loss-limit

    Request Body:
        amount: 新しい限度額（円）

    Returns:
        変更結果
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    if "amount" not in body:
        return bad_request_response("amount is required", event=event)

    amount = body["amount"]
    if isinstance(amount, bool) or not isinstance(amount, int):
        return bad_request_response("amount must be an integer", event=event)

    user_repo = Dependencies.get_user_repository()
    change_repo = Dependencies.get_loss_limit_change_repository()
    use_case = UpdateLossLimitUseCase(user_repo, change_repo)

    try:
        result = use_case.execute(user_id, amount)
    except UpdateUserNotFoundError:
        return not_found_response("User", event=event)
    except LossLimitNotSetError:
        return bad_request_response("Loss limit is not set yet", event=event)
    except PendingChangeExistsError:
        return bad_request_response(
            "A pending change request already exists", event=event
        )
    except UpdateInvalidAmountError as e:
        return bad_request_response(str(e), event=event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    return success_response(
        {
            "change_id": str(result.change.change_id),
            "change_type": result.change.change_type.value,
            "status": result.change.status.value,
            "current_limit": result.change.current_limit.value,
            "requested_limit": result.change.requested_limit.value,
            "effective_at": result.change.effective_at.isoformat(),
            "applied_immediately": result.applied_immediately,
        },
        event=event,
    )


def check_loss_limit_handler(event: dict, context: Any) -> dict:
    """購入可否をチェックする.

    GET /users/loss-limit/check?amount={amount}

    Query Parameters:
        amount: 購入金額（円）

    Returns:
        チェック結果
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    amount_str = get_query_parameter(event, "amount")
    if amount_str is None:
        return bad_request_response("amount query parameter is required", event=event)

    try:
        amount = int(amount_str)
    except ValueError:
        return bad_request_response("amount must be an integer", event=event)

    if amount <= 0:
        return bad_request_response("amount must be positive", event=event)

    user_repo = Dependencies.get_user_repository()
    use_case = CheckLossLimitUseCase(user_repo)

    try:
        result = use_case.execute(user_id, amount)
    except CheckUserNotFoundError:
        return not_found_response("User", event=event)

    return success_response(
        {
            "can_purchase": result.can_purchase,
            "remaining_amount": result.remaining_amount.value if result.remaining_amount else None,
            "warning_level": result.warning_level.value,
            "message": result.message,
        },
        event=event,
    )
