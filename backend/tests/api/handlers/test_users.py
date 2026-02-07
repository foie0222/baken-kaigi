"""ユーザーAPI ハンドラーのテスト."""
import json
from datetime import date, datetime, timezone

import pytest

from src.api.dependencies import Dependencies
from src.api.handlers.users import delete_account, get_user_profile, update_user_profile
from src.domain.entities import User
from src.domain.enums import AuthProvider
from src.domain.identifiers import UserId
from src.domain.value_objects import DateOfBirth, DisplayName, Email
from src.infrastructure.repositories import InMemoryUserRepository


def _make_event(sub: str | None = None, body: dict | None = None) -> dict:
    """テスト用イベントを作成する."""
    event: dict = {}
    if sub is not None:
        event["requestContext"] = {
            "authorizer": {"claims": {"sub": sub}}
        }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


def _make_user(**overrides) -> User:
    defaults = {
        "user_id": UserId("user-123"),
        "email": Email("test@example.com"),
        "display_name": DisplayName("太郎"),
        "date_of_birth": DateOfBirth(date(2000, 1, 1)),
        "terms_accepted_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "privacy_accepted_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "auth_provider": AuthProvider.COGNITO,
    }
    defaults.update(overrides)
    return User(**defaults)


@pytest.fixture(autouse=True)
def _reset_dependencies():
    Dependencies.reset()
    repo = InMemoryUserRepository()
    Dependencies.set_user_repository(repo)
    yield
    Dependencies.reset()


class TestGetUserProfile:
    """プロフィール取得のテスト."""

    def test_プロフィールを取得できる(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user())
        event = _make_event(sub="user-123")
        resp = get_user_profile(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["user_id"] == "user-123"
        assert body["email"] == "test@example.com"

    def test_未認証で401(self):
        resp = get_user_profile(_make_event(), None)
        assert resp["statusCode"] == 401

    def test_存在しないユーザーで404(self):
        event = _make_event(sub="nonexistent")
        resp = get_user_profile(event, None)
        assert resp["statusCode"] == 404


class TestUpdateUserProfile:
    """プロフィール更新のテスト."""

    def test_表示名を更新できる(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user())
        event = _make_event(sub="user-123", body={"display_name": "花子"})
        resp = update_user_profile(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["display_name"] == "花子"

    def test_未認証で401(self):
        resp = update_user_profile(_make_event(body={"display_name": "花子"}), None)
        assert resp["statusCode"] == 401

    def test_パラメータなしで400(self):
        event = _make_event(sub="user-123", body={})
        resp = update_user_profile(event, None)
        assert resp["statusCode"] == 400


class TestDeleteAccount:
    """アカウント削除のテスト."""

    def test_削除リクエストできる(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user())
        event = _make_event(sub="user-123")
        resp = delete_account(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["days_until_permanent_deletion"] in (29, 30)

    def test_未認証で401(self):
        resp = delete_account(_make_event(), None)
        assert resp["statusCode"] == 401
