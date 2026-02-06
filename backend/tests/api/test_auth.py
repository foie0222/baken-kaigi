"""認証ユーティリティのテスト."""
import pytest

from src.api.auth import AuthenticationError, get_authenticated_user_id, require_authenticated_user_id


class TestGetAuthenticatedUserId:
    """get_authenticated_user_idのテスト."""

    def test_認証済みイベントからユーザーIDを取得(self):
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "user-123",
                    }
                }
            }
        }
        user_id = get_authenticated_user_id(event)
        assert user_id is not None
        assert user_id.value == "user-123"

    def test_未認証イベントでNoneを返す(self):
        event = {}
        assert get_authenticated_user_id(event) is None

    def test_authorizerなしでNoneを返す(self):
        event = {"requestContext": {}}
        assert get_authenticated_user_id(event) is None

    def test_claimsなしでNoneを返す(self):
        event = {"requestContext": {"authorizer": {}}}
        assert get_authenticated_user_id(event) is None

    def test_subなしでNoneを返す(self):
        event = {"requestContext": {"authorizer": {"claims": {}}}}
        assert get_authenticated_user_id(event) is None


class TestRequireAuthenticatedUserId:
    """require_authenticated_user_idのテスト."""

    def test_認証済みイベントからユーザーIDを取得(self):
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {"sub": "user-456"}
                }
            }
        }
        user_id = require_authenticated_user_id(event)
        assert user_id.value == "user-456"

    def test_未認証でAuthenticationErrorが発生(self):
        with pytest.raises(AuthenticationError, match="Authentication required"):
            require_authenticated_user_id({})
