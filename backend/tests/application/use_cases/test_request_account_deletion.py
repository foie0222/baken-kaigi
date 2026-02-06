"""RequestAccountDeletionUseCaseのテスト."""
from datetime import date, datetime, timezone

import pytest

from src.application.use_cases import RequestAccountDeletionUseCase, UserNotFoundError
from src.domain.entities import User
from src.domain.enums import AuthProvider, UserStatus
from src.domain.identifiers import UserId
from src.domain.value_objects import DateOfBirth, DisplayName, Email
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


class TestRequestAccountDeletionUseCase:
    """アカウント削除リクエストのテスト."""

    def test_削除リクエストできる(self):
        repo = InMemoryUserRepository()
        repo.save(_make_user())
        use_case = RequestAccountDeletionUseCase(repo)
        result = use_case.execute(UserId("user-123"))
        assert result.user_id.value == "user-123"
        assert result.deletion_requested_at is not None
        assert result.days_until_permanent_deletion in (29, 30)

    def test_削除後のユーザーステータスがPENDING_DELETION(self):
        repo = InMemoryUserRepository()
        repo.save(_make_user())
        use_case = RequestAccountDeletionUseCase(repo)
        use_case.execute(UserId("user-123"))
        user = repo.find_by_id(UserId("user-123"))
        assert user is not None
        assert user.status == UserStatus.PENDING_DELETION

    def test_存在しないユーザーでエラー(self):
        repo = InMemoryUserRepository()
        use_case = RequestAccountDeletionUseCase(repo)
        with pytest.raises(UserNotFoundError):
            use_case.execute(UserId("nonexistent"))
