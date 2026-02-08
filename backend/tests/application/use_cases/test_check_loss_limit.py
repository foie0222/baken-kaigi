"""CheckLossLimitUseCaseのテスト."""
from datetime import date, datetime, timezone

import pytest

from src.application.use_cases.check_loss_limit import (
    CheckLossLimitUseCase,
    UserNotFoundError,
)
from src.domain.entities import User
from src.domain.enums import AuthProvider, WarningLevel
from src.domain.identifiers import UserId
from src.domain.value_objects import DateOfBirth, DisplayName, Email, Money
from src.infrastructure.repositories import InMemoryUserRepository


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


class TestCheckLossLimitUseCase:
    """購入可否チェックユースケースのテスト."""

    def test_限度額未設定なら購入可能(self):
        user_repo = InMemoryUserRepository()
        user_repo.save(_make_user())
        use_case = CheckLossLimitUseCase(user_repo)

        result = use_case.execute(UserId("user-123"), 10000)

        assert result.can_purchase is True
        assert result.warning_level == WarningLevel.NONE

    def test_限度額内なら購入可能(self):
        user_repo = InMemoryUserRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000), total_loss_this_month=Money.of(10000)))
        use_case = CheckLossLimitUseCase(user_repo)

        result = use_case.execute(UserId("user-123"), 5000)

        assert result.can_purchase is True
        assert result.warning_level == WarningLevel.NONE

    def test_限度額の80パーセント以上で注意(self):
        user_repo = InMemoryUserRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000), total_loss_this_month=Money.of(35000)))
        use_case = CheckLossLimitUseCase(user_repo)

        result = use_case.execute(UserId("user-123"), 5000)

        assert result.can_purchase is True
        assert result.warning_level == WarningLevel.CAUTION

    def test_限度額超過で購入不可(self):
        user_repo = InMemoryUserRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000), total_loss_this_month=Money.of(45000)))
        use_case = CheckLossLimitUseCase(user_repo)

        result = use_case.execute(UserId("user-123"), 10000)

        assert result.can_purchase is False
        assert result.warning_level == WarningLevel.WARNING

    def test_存在しないユーザーでエラー(self):
        user_repo = InMemoryUserRepository()
        use_case = CheckLossLimitUseCase(user_repo)

        with pytest.raises(UserNotFoundError):
            use_case.execute(UserId("nonexistent"), 10000)
