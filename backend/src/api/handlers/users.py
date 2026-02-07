"""ユーザーAPI ハンドラー."""
from typing import Any

from src.api.auth import AuthenticationError, require_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.request import get_body
from src.api.response import (
    bad_request_response,
    not_found_response,
    success_response,
    unauthorized_response,
)
from src.application.use_cases import (
    GetUserProfileUseCase,
    RequestAccountDeletionUseCase,
    UpdateUserProfileUseCase,
    UserNotFoundError,
)


def get_user_profile(event: dict, context: Any) -> dict:
    """ユーザープロフィールを取得する.

    GET /users/profile

    Returns:
        プロフィール情報
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response()

    repository = Dependencies.get_user_repository()
    use_case = GetUserProfileUseCase(repository)

    try:
        result = use_case.execute(user_id)
    except UserNotFoundError:
        return not_found_response("User")

    return success_response(
        {
            "user_id": str(result.user_id),
            "email": str(result.email),
            "display_name": str(result.display_name),
            "date_of_birth": str(result.date_of_birth),
            "auth_provider": result.auth_provider.value,
            "status": result.status.value,
            "created_at": result.created_at.isoformat(),
        }
    )


def update_user_profile(event: dict, context: Any) -> dict:
    """ユーザープロフィールを更新する.

    PUT /users/profile

    Request Body:
        display_name: 表示名（オプション）
        email: メールアドレス（オプション）

    Returns:
        更新結果
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response()

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e))

    display_name = body.get("display_name")
    email = body.get("email")

    if display_name is not None and not isinstance(display_name, str):
        return bad_request_response("display_name must be a string")
    if email is not None and not isinstance(email, str):
        return bad_request_response("email must be a string")

    if display_name is None and email is None:
        return bad_request_response("At least one of display_name or email is required")

    repository = Dependencies.get_user_repository()
    use_case = UpdateUserProfileUseCase(repository)

    try:
        result = use_case.execute(user_id, display_name=display_name, email=email)
    except UserNotFoundError:
        return not_found_response("User")
    except ValueError as e:
        return bad_request_response(str(e))

    return success_response(
        {
            "user_id": str(result.user_id),
            "email": str(result.email),
            "display_name": str(result.display_name),
        }
    )


def delete_account(event: dict, context: Any) -> dict:
    """アカウント削除をリクエストする.

    DELETE /users/account

    Returns:
        削除リクエスト結果
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response()

    repository = Dependencies.get_user_repository()
    use_case = RequestAccountDeletionUseCase(repository)

    try:
        result = use_case.execute(user_id)
    except UserNotFoundError:
        return not_found_response("User")
    except ValueError as e:
        return bad_request_response(str(e))

    return success_response(
        {
            "user_id": str(result.user_id),
            "deletion_requested_at": result.deletion_requested_at.isoformat(),
            "days_until_permanent_deletion": result.days_until_permanent_deletion,
        }
    )
