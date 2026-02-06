"""InMemoryUserRepositoryのテスト."""
from datetime import date, datetime, timezone

from src.domain.entities import User
from src.domain.enums import AuthProvider
from src.domain.identifiers import UserId
from src.domain.value_objects import DateOfBirth, DisplayName, Email
from src.infrastructure.repositories import InMemoryUserRepository


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


class TestInMemoryUserRepository:
    """InMemoryUserRepositoryのテスト."""

    def test_保存と取得(self):
        repo = InMemoryUserRepository()
        user = _make_user()
        repo.save(user)
        found = repo.find_by_id(UserId("user-123"))
        assert found is not None
        assert found.user_id.value == "user-123"

    def test_存在しないIDの検索(self):
        repo = InMemoryUserRepository()
        assert repo.find_by_id(UserId("nonexistent")) is None

    def test_メールアドレスで検索(self):
        repo = InMemoryUserRepository()
        user = _make_user()
        repo.save(user)
        found = repo.find_by_email(Email("test@example.com"))
        assert found is not None
        assert found.email.value == "test@example.com"

    def test_存在しないメールアドレスの検索(self):
        repo = InMemoryUserRepository()
        assert repo.find_by_email(Email("nonexistent@example.com")) is None

    def test_削除(self):
        repo = InMemoryUserRepository()
        user = _make_user()
        repo.save(user)
        repo.delete(UserId("user-123"))
        assert repo.find_by_id(UserId("user-123")) is None

    def test_存在しないIDの削除はエラーにならない(self):
        repo = InMemoryUserRepository()
        repo.delete(UserId("nonexistent"))  # エラーにならないことを確認

    def test_上書き保存(self):
        repo = InMemoryUserRepository()
        user = _make_user()
        repo.save(user)
        user.update_display_name(DisplayName("花子"))
        repo.save(user)
        found = repo.find_by_id(UserId("user-123"))
        assert found is not None
        assert found.display_name.value == "花子"
