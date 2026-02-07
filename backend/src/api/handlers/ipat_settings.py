"""IPAT設定APIハンドラー."""
from typing import Any

from src.api.auth import AuthenticationError, require_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.request import get_body
from src.api.response import (
    bad_request_response,
    success_response,
    unauthorized_response,
)
from src.application.use_cases.delete_ipat_credentials import DeleteIpatCredentialsUseCase
from src.application.use_cases.get_ipat_status import GetIpatStatusUseCase
from src.application.use_cases.save_ipat_credentials import SaveIpatCredentialsUseCase


def save_ipat_credentials_handler(event: dict, context: Any) -> dict:
    """IPAT認証情報を保存する.

    PUT /settings/ipat
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response()

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e))

    card_number = body.get("card_number")
    birthday = body.get("birthday")
    pin = body.get("pin")
    dummy_pin = body.get("dummy_pin")

    if not all([card_number, birthday, pin, dummy_pin]):
        return bad_request_response(
            "card_number, birthday, pin, dummy_pin are all required"
        )

    use_case = SaveIpatCredentialsUseCase(
        credentials_provider=Dependencies.get_credentials_provider(),
    )

    try:
        use_case.execute(
            user_id=user_id.value,
            card_number=card_number,
            birthday=birthday,
            pin=pin,
            dummy_pin=dummy_pin,
        )
    except ValueError as e:
        return bad_request_response(str(e))

    return success_response({"message": "IPAT credentials saved"})


def get_ipat_status_handler(event: dict, context: Any) -> dict:
    """IPAT設定ステータスを取得する.

    GET /settings/ipat
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response()

    use_case = GetIpatStatusUseCase(
        credentials_provider=Dependencies.get_credentials_provider(),
    )
    result = use_case.execute(user_id.value)

    return success_response(result)


def delete_ipat_credentials_handler(event: dict, context: Any) -> dict:
    """IPAT認証情報を削除する.

    DELETE /settings/ipat
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response()

    use_case = DeleteIpatCredentialsUseCase(
        credentials_provider=Dependencies.get_credentials_provider(),
    )
    use_case.execute(user_id.value)

    return success_response({"message": "IPAT credentials deleted"})
