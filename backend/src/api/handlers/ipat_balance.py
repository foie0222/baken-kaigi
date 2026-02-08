"""IPAT残高APIハンドラー."""
import logging
from typing import Any

from src.api.auth import AuthenticationError, require_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.response import (
    bad_request_response,
    internal_error_response,
    success_response,
    unauthorized_response,
)
from src.domain.ports import IpatGatewayError

logger = logging.getLogger(__name__)
from src.application.use_cases.get_ipat_balance import (
    CredentialsNotFoundError,
    GetIpatBalanceUseCase,
)


def get_ipat_balance_handler(event: dict, context: Any) -> dict:
    """IPAT残高を取得する.

    GET /ipat/balance
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    use_case = GetIpatBalanceUseCase(
        credentials_provider=Dependencies.get_credentials_provider(),
        ipat_gateway=Dependencies.get_ipat_gateway(),
    )

    try:
        balance = use_case.execute(user_id.value)
    except CredentialsNotFoundError:
        return bad_request_response("IPAT credentials not configured", event=event)
    except IpatGatewayError as e:
        logger.error("IpatGatewayError: %s", e)
        return internal_error_response("IPAT通信エラーが発生しました", event=event)

    return success_response({
        "bet_dedicated_balance": balance.bet_dedicated_balance,
        "settle_possible_balance": balance.settle_possible_balance,
        "bet_balance": balance.bet_balance,
        "limit_vote_amount": balance.limit_vote_amount,
    }, event=event)
