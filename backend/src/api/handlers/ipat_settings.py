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
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    inet_id = body.get("inet_id")
    subscriber_number = body.get("subscriber_number")
    pin = body.get("pin")
    pars_number = body.get("pars_number")

    if not all([inet_id, subscriber_number, pin, pars_number]):
        return bad_request_response(
            "inet_id, subscriber_number, pin, pars_number are all required",
            event=event,
        )

    for field_name, field_value in [
        ("inet_id", inet_id),
        ("subscriber_number", subscriber_number),
        ("pin", pin),
        ("pars_number", pars_number),
    ]:
        if not isinstance(field_value, str):
            return bad_request_response(
                f"{field_name} must be a string",
                event=event,
            )

    use_case = SaveIpatCredentialsUseCase(
        credentials_provider=Dependencies.get_credentials_provider(),
    )

    try:
        use_case.execute(
            user_id=user_id.value,
            inet_id=inet_id,
            subscriber_number=subscriber_number,
            pin=pin,
            pars_number=pars_number,
        )
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    return success_response({"message": "IPAT credentials saved"}, event=event)


def get_ipat_status_handler(event: dict, context: Any) -> dict:
    """IPAT設定ステータスを取得する.

    GET /settings/ipat
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    use_case = GetIpatStatusUseCase(
        credentials_provider=Dependencies.get_credentials_provider(),
    )
    result = use_case.execute(user_id.value)

    return success_response(result, event=event)


def delete_ipat_credentials_handler(event: dict, context: Any) -> dict:
    """IPAT認証情報を削除する.

    DELETE /settings/ipat
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    use_case = DeleteIpatCredentialsUseCase(
        credentials_provider=Dependencies.get_credentials_provider(),
    )
    use_case.execute(user_id.value)

    return success_response({"message": "IPAT credentials deleted"}, event=event)
