"""Cognitoトリガーのテスト."""
import pytest

from src.api.dependencies import Dependencies
from src.api.handlers.cognito_triggers import post_confirmation
from src.domain.identifiers import UserId
from src.infrastructure.repositories import InMemoryUserRepository


@pytest.fixture(autouse=True)
def _reset_dependencies():
    Dependencies.reset()
    repo = InMemoryUserRepository()
    Dependencies.set_user_repository(repo)
    yield
    Dependencies.reset()


class TestPostConfirmation:
    """Post Confirmationトリガーのテスト."""

    def test_ユーザーが作成される(self):
        event = {
            "triggerSource": "PostConfirmation_ConfirmSignUp",
            "request": {
                "userAttributes": {
                    "sub": "user-abc",
                    "email": "abc@example.com",
                    "custom:display_name": "テストユーザー",
                    "birthdate": "2000-01-15",
                }
            },
        }
        result = post_confirmation(event, None)
        assert result == event  # イベントをそのまま返す

        repo = Dependencies.get_user_repository()
        user = repo.find_by_id(UserId("user-abc"))
        assert user is not None
        assert user.email.value == "abc@example.com"
        assert user.display_name.value == "テストユーザー"

    def test_display_nameがない場合メールのローカル部分を使用(self):
        event = {
            "triggerSource": "PostConfirmation_ConfirmSignUp",
            "request": {
                "userAttributes": {
                    "sub": "user-xyz",
                    "email": "xyz@example.com",
                    "birthdate": "1995-06-20",
                }
            },
        }
        post_confirmation(event, None)
        repo = Dependencies.get_user_repository()
        user = repo.find_by_id(UserId("user-xyz"))
        assert user is not None
        assert user.display_name.value == "xyz"

    def test_重複呼び出しはエラーにならない(self):
        event = {
            "triggerSource": "PostConfirmation_ConfirmSignUp",
            "request": {
                "userAttributes": {
                    "sub": "user-dup",
                    "email": "dup@example.com",
                    "custom:display_name": "重複テスト",
                    "birthdate": "2000-01-01",
                }
            },
        }
        post_confirmation(event, None)
        result = post_confirmation(event, None)  # 2回目もエラーにならない
        assert result == event
