"""認証ユーティリティ."""
from src.domain.identifiers import UserId


def get_authenticated_user_id(event: dict) -> UserId | None:
    """認証済みユーザーIDを取得する.

    Cognito Authorizer が設定されたエンドポイントでは、
    event["requestContext"]["authorizer"]["claims"]["sub"] にユーザーIDが含まれる。

    Args:
        event: Lambda イベント

    Returns:
        ユーザーID（未認証の場合はNone）
    """
    try:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        sub = claims.get("sub")
        if sub:
            return UserId(sub)
    except (AttributeError, TypeError):
        # event構造が想定外の場合（値がdictでない等）は未認証として扱う
        pass
    return None


def require_authenticated_user_id(event: dict) -> UserId:
    """認証済みユーザーIDを取得する（必須）.

    Args:
        event: Lambda イベント

    Returns:
        ユーザーID

    Raises:
        AuthenticationError: 未認証の場合
    """
    user_id = get_authenticated_user_id(event)
    if user_id is None:
        raise AuthenticationError("Authentication required")
    return user_id


class AuthenticationError(Exception):
    """認証エラー."""

    pass
