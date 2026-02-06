"""Userエンティティのテスト."""
from datetime import date, datetime, timezone

import pytest

from src.domain.entities import User
from src.domain.enums import AuthProvider, UserStatus
from src.domain.identifiers import UserId
from src.domain.value_objects import DateOfBirth, DisplayName, Email


def _make_user(**overrides) -> User:
    """テスト用ユーザーを作成する."""
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


class TestUser:
    """Userエンティティのテスト."""

    def test_ユーザーを生成できる(self):
        user = _make_user()
        assert user.user_id.value == "user-123"
        assert user.email.value == "test@example.com"
        assert user.status == UserStatus.ACTIVE

    def test_表示名を更新できる(self):
        user = _make_user()
        old_updated_at = user.updated_at
        user.update_display_name(DisplayName("花子"))
        assert user.display_name.value == "花子"
        assert user.updated_at > old_updated_at

    def test_メールを更新できる(self):
        user = _make_user()
        user.update_email(Email("new@example.com"))
        assert user.email.value == "new@example.com"

    def test_削除リクエストできる(self):
        user = _make_user()
        user.request_deletion()
        assert user.status == UserStatus.PENDING_DELETION
        assert user.deletion_requested_at is not None

    def test_削除済みユーザーの削除リクエストでエラー(self):
        user = _make_user(status=UserStatus.DELETED)
        with pytest.raises(ValueError, match="already deleted"):
            user.request_deletion()

    def test_削除をキャンセルできる(self):
        user = _make_user()
        user.request_deletion()
        user.cancel_deletion()
        assert user.status == UserStatus.ACTIVE
        assert user.deletion_requested_at is None

    def test_アクティブユーザーの削除キャンセルでエラー(self):
        user = _make_user()
        with pytest.raises(ValueError, match="not pending deletion"):
            user.cancel_deletion()

    def test_is_active(self):
        user = _make_user()
        assert user.is_active() is True

    def test_is_pending_deletion(self):
        user = _make_user()
        user.request_deletion()
        assert user.is_pending_deletion() is True
