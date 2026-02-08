"""GetLossLimitUseCaseのテスト."""
from datetime import date, datetime, timedelta, timezone

import pytest

from src.application.use_cases.get_loss_limit import GetLossLimitUseCase, UserNotFoundError
from src.domain.entities import LossLimitChange, User
from src.domain.enums import AuthProvider, LossLimitChangeStatus, LossLimitChangeType
from src.domain.identifiers import LossLimitChangeId, UserId
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


class TestGetLossLimitUseCase:
    """負け額限度額取得ユースケースのテスト."""

    def test_限度額未設定のユーザー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user())
        use_case = GetLossLimitUseCase(user_repo, change_repo)

        result = use_case.execute(UserId("user-123"))

        assert result.loss_limit is None
        assert result.remaining_amount is None
        assert result.total_loss_this_month == Money.zero()
        assert result.pending_changes == []

    def test_限度額設定済みのユーザー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user = _make_user(loss_limit=Money.of(50000), total_loss_this_month=Money.of(10000))
        user_repo.save(user)
        use_case = GetLossLimitUseCase(user_repo, change_repo)

        result = use_case.execute(UserId("user-123"))

        assert result.loss_limit == Money.of(50000)
        assert result.remaining_amount == Money.of(40000)
        assert result.total_loss_this_month == Money.of(10000)

    def test_保留中の変更リクエストがある場合(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user = _make_user(loss_limit=Money.of(50000))
        user_repo.save(user)

        pending_change = LossLimitChange(
            change_id=LossLimitChangeId("change-1"),
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
            change_type=LossLimitChangeType.INCREASE,
            status=LossLimitChangeStatus.PENDING,
            effective_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        change_repo.save(pending_change)
        use_case = GetLossLimitUseCase(user_repo, change_repo)

        result = use_case.execute(UserId("user-123"))

        assert len(result.pending_changes) == 1
        assert result.pending_changes[0].requested_limit == Money.of(100000)

    def test_存在しないユーザーでエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        use_case = GetLossLimitUseCase(user_repo, change_repo)

        with pytest.raises(UserNotFoundError):
            use_case.execute(UserId("nonexistent"))
