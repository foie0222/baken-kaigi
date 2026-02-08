"""SetLossLimitUseCaseのテスト."""
from datetime import date, datetime, timezone

import pytest

from src.application.use_cases.set_loss_limit import (
    InvalidLossLimitAmountError,
    LossLimitAlreadySetError,
    SetLossLimitUseCase,
    UserNotFoundError,
)
from src.domain.entities import User
from src.domain.enums import AuthProvider
from src.domain.identifiers import UserId
from src.domain.value_objects import DateOfBirth, DisplayName, Email, Money
from src.infrastructure.repositories import (
    InMemoryLossLimitChangeRepository,
    InMemoryUserRepository,
)


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


class TestSetLossLimitUseCase:
    """負け額限度額設定ユースケースのテスト."""

    def test_初回限度額を設定できる(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user())
        use_case = SetLossLimitUseCase(user_repo, change_repo)

        result = use_case.execute(UserId("user-123"), 50000)

        assert result.loss_limit == Money.of(50000)
        # ユーザーに反映されていること
        saved_user = user_repo.find_by_id(UserId("user-123"))
        assert saved_user.loss_limit == Money.of(50000)
        # 変更履歴が保存されていること
        changes = change_repo.find_by_user_id(UserId("user-123"))
        assert len(changes) == 1

    def test_最小金額で設定できる(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user())
        use_case = SetLossLimitUseCase(user_repo, change_repo)

        result = use_case.execute(UserId("user-123"), 1000)

        assert result.loss_limit == Money.of(1000)

    def test_最大金額で設定できる(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user())
        use_case = SetLossLimitUseCase(user_repo, change_repo)

        result = use_case.execute(UserId("user-123"), 1000000)

        assert result.loss_limit == Money.of(1000000)

    def test_最小金額未満でエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user())
        use_case = SetLossLimitUseCase(user_repo, change_repo)

        with pytest.raises(InvalidLossLimitAmountError):
            use_case.execute(UserId("user-123"), 999)

    def test_最大金額超過でエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user())
        use_case = SetLossLimitUseCase(user_repo, change_repo)

        with pytest.raises(InvalidLossLimitAmountError):
            use_case.execute(UserId("user-123"), 1000001)

    def test_既に設定済みでエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000)))
        use_case = SetLossLimitUseCase(user_repo, change_repo)

        with pytest.raises(LossLimitAlreadySetError):
            use_case.execute(UserId("user-123"), 30000)

    def test_存在しないユーザーでエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        use_case = SetLossLimitUseCase(user_repo, change_repo)

        with pytest.raises(UserNotFoundError):
            use_case.execute(UserId("nonexistent"), 50000)
