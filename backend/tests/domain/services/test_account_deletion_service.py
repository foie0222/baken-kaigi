"""AccountDeletionServiceのテスト."""
from datetime import date, datetime, timedelta, timezone

from src.domain.entities import User
from src.domain.enums import AuthProvider, UserStatus
from src.domain.identifiers import UserId
from src.domain.services import AccountDeletionService
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


class TestAccountDeletionService:
    """アカウント削除サービスのテスト."""

    def test_30日経過で物理削除可能(self):
        user = _make_user(
            status=UserStatus.PENDING_DELETION,
            deletion_requested_at=datetime.now(timezone.utc) - timedelta(days=31),
        )
        assert AccountDeletionService.is_ready_for_permanent_deletion(user) is True

    def test_29日では物理削除不可(self):
        user = _make_user(
            status=UserStatus.PENDING_DELETION,
            deletion_requested_at=datetime.now(timezone.utc) - timedelta(days=29),
        )
        assert AccountDeletionService.is_ready_for_permanent_deletion(user) is False

    def test_アクティブユーザーは物理削除不可(self):
        user = _make_user()
        assert AccountDeletionService.is_ready_for_permanent_deletion(user) is False

    def test_残り日数計算(self):
        # 正確に20日前の同時刻を基準にすることで端数を防ぐ
        user = _make_user(
            status=UserStatus.PENDING_DELETION,
            deletion_requested_at=datetime.now(timezone.utc) - timedelta(days=20),
        )
        days = AccountDeletionService.days_until_permanent_deletion(user)
        assert days is not None
        # timedelta(days=20)前なので、残り約10日（秒単位の誤差で9になる場合あり）
        assert 9 <= days <= 10

    def test_アクティブユーザーの残り日数はNone(self):
        user = _make_user()
        assert AccountDeletionService.days_until_permanent_deletion(user) is None
