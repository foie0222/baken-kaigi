"""UpdateLossLimitUseCaseのテスト."""
from datetime import date, datetime, timezone

import pytest

from src.application.use_cases.update_loss_limit import (
    InvalidLossLimitAmountError,
    LossLimitNotSetError,
    PendingChangeExistsError,
    UpdateLossLimitUseCase,
    UserNotFoundError,
)
from src.domain.entities import User
from src.domain.enums import AuthProvider, LossLimitChangeStatus, LossLimitChangeType
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


class TestUpdateLossLimitUseCase:
    """負け額限度額変更ユースケースのテスト."""

    def test_減額は即時反映される(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000)))
        use_case = UpdateLossLimitUseCase(user_repo, change_repo)

        result = use_case.execute(UserId("user-123"), 30000)

        assert result.applied_immediately is True
        assert result.change.change_type == LossLimitChangeType.DECREASE
        assert result.change.requested_limit == Money.of(30000)
        # ユーザーに即時反映
        saved_user = user_repo.find_by_id(UserId("user-123"))
        assert saved_user.loss_limit == Money.of(30000)

    def test_増額は保留になる(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000)))
        use_case = UpdateLossLimitUseCase(user_repo, change_repo)

        result = use_case.execute(UserId("user-123"), 100000)

        assert result.applied_immediately is False
        assert result.change.change_type == LossLimitChangeType.INCREASE
        assert result.change.status == LossLimitChangeStatus.PENDING
        assert result.change.requested_limit == Money.of(100000)
        # ユーザーの限度額は変わらない
        saved_user = user_repo.find_by_id(UserId("user-123"))
        assert saved_user.loss_limit == Money.of(50000)

    def test_変更履歴が保存される(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000)))
        use_case = UpdateLossLimitUseCase(user_repo, change_repo)

        use_case.execute(UserId("user-123"), 30000)

        changes = change_repo.find_by_user_id(UserId("user-123"))
        assert len(changes) == 1

    def test_限度額未設定でエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user())
        use_case = UpdateLossLimitUseCase(user_repo, change_repo)

        with pytest.raises(LossLimitNotSetError):
            use_case.execute(UserId("user-123"), 50000)

    def test_範囲外の金額でエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000)))
        use_case = UpdateLossLimitUseCase(user_repo, change_repo)

        with pytest.raises(InvalidLossLimitAmountError):
            use_case.execute(UserId("user-123"), 999)

        with pytest.raises(InvalidLossLimitAmountError):
            use_case.execute(UserId("user-123"), 1000001)

    def test_存在しないユーザーでエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        use_case = UpdateLossLimitUseCase(user_repo, change_repo)

        with pytest.raises(UserNotFoundError):
            use_case.execute(UserId("nonexistent"), 50000)

    def test_PENDING中に新規リクエストでエラー(self):
        user_repo = InMemoryUserRepository()
        change_repo = InMemoryLossLimitChangeRepository()
        user_repo.save(_make_user(loss_limit=Money.of(50000)))
        use_case = UpdateLossLimitUseCase(user_repo, change_repo)

        # 増額リクエスト（PENDING状態になる）
        use_case.execute(UserId("user-123"), 100000)

        # さらに変更リクエストを出すとエラー
        with pytest.raises(PendingChangeExistsError):
            use_case.execute(UserId("user-123"), 80000)
