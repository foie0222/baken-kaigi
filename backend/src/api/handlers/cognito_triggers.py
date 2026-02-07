"""Cognito トリガーハンドラー."""
import logging
from typing import Any

from src.api.dependencies import Dependencies
from src.application.use_cases import RegisterUserUseCase, UserAlreadyExistsError

logger = logging.getLogger(__name__)


def post_confirmation(event: dict, context: Any) -> dict:
    """Cognito Post Confirmation トリガー.

    ユーザーがメール確認を完了した時に呼び出される。
    DynamoDB にユーザーレコードを作成する。

    Args:
        event: Cognito トリガーイベント
        context: Lambda コンテキスト

    Returns:
        イベント（Cognito に返す）
    """
    user_attributes = event.get("request", {}).get("userAttributes", {})

    user_id = user_attributes.get("sub", "")
    email = user_attributes.get("email", "")
    display_name = user_attributes.get("custom:display_name", email.split("@")[0] if email else "ユーザー")
    date_of_birth = user_attributes.get("birthdate", "2000-01-01")

    # 認証プロバイダの判定
    trigger_source = event.get("triggerSource", "")
    if "ExternalProvider" in trigger_source:
        provider_name = event.get("userName", "").split("_")[0].lower()
        if provider_name in ("google", "apple"):
            auth_provider = provider_name
        else:
            auth_provider = "cognito"
    else:
        auth_provider = "cognito"

    repository = Dependencies.get_user_repository()
    use_case = RegisterUserUseCase(repository)

    try:
        use_case.execute(
            user_id=user_id,
            email=email,
            display_name=display_name,
            date_of_birth_str=date_of_birth,
            auth_provider=auth_provider,
        )
        logger.info("User registered: %s", user_id)
    except UserAlreadyExistsError:
        logger.info("User already exists: %s (idempotent)", user_id)
    except (ValueError, TypeError) as exc:
        logger.exception("Failed to register user: %s", user_id)
        # Cognito トリガーはエラーを返してもサインアップを止めないように
        # 値オブジェクト生成時のバリデーションエラーのみ握りつぶす
        logger.warning("Suppressed error for user %s: %s", user_id, exc)
    except Exception:
        logger.exception("Unexpected error registering user: %s", user_id)
        raise

    return event
