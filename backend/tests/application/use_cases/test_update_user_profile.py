"""UpdateUserProfileUseCaseのテスト."""
from datetime import date, datetime, timezone

import pytest

from src.application.use_cases import UpdateUserProfileUseCase, UserNotFoundError
from src.domain.entities import User
from src.domain.enums import AuthProvider
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


class TestUpdateUserProfileUseCase:
    """プロフィール更新ユースケースのテスト."""

    def test_表示名を更新できる(self):
        repo = InMemoryUserRepository()
        repo.save(_make_user())
        use_case = UpdateUserProfileUseCase(repo)
        result = use_case.execute(UserId("user-123"), display_name="花子")
        assert result.display_name.value == "花子"

    def test_メールを更新できる(self):
        repo = InMemoryUserRepository()
        repo.save(_make_user())
        use_case = UpdateUserProfileUseCase(repo)
        result = use_case.execute(UserId("user-123"), email="new@example.com")
        assert result.email.value == "new@example.com"

    def test_両方を同時に更新できる(self):
        repo = InMemoryUserRepository()
        repo.save(_make_user())
        use_case = UpdateUserProfileUseCase(repo)
        result = use_case.execute(UserId("user-123"), display_name="花子", email="new@example.com")
        assert result.display_name.value == "花子"
        assert result.email.value == "new@example.com"

    def test_存在しないユーザーでエラー(self):
        repo = InMemoryUserRepository()
        use_case = UpdateUserProfileUseCase(repo)
        with pytest.raises(UserNotFoundError):
            use_case.execute(UserId("nonexistent"), display_name="花子")
