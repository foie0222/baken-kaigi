"""UserStatus列挙型のテスト."""
from src.domain.enums import UserStatus


class TestUserStatus:
    """UserStatusのテスト."""

    def test_ACTIVEの値(self):
        assert UserStatus.ACTIVE.value == "active"

    def test_SUSPENDEDの値(self):
        assert UserStatus.SUSPENDED.value == "suspended"

    def test_PENDING_DELETIONの値(self):
        assert UserStatus.PENDING_DELETION.value == "pending_deletion"

    def test_DELETEDの値(self):
        assert UserStatus.DELETED.value == "deleted"

    def test_文字列から生成できる(self):
        assert UserStatus("active") == UserStatus.ACTIVE

    def test_全メンバーが4つ(self):
        assert len(UserStatus) == 4
