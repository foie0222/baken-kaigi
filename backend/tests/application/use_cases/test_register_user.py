"""RegisterUserUseCaseのテスト."""
import pytest

from src.application.use_cases import RegisterUserUseCase, UserAlreadyExistsError
from src.infrastructure.repositories import InMemoryUserRepository


class TestRegisterUserUseCase:
    """ユーザー登録ユースケースのテスト."""

    def test_新規ユーザーを登録できる(self):
        repo = InMemoryUserRepository()
        use_case = RegisterUserUseCase(repo)
        result = use_case.execute(
            user_id="user-123",
            email="test@example.com",
            display_name="太郎",
            date_of_birth_str="2000-01-01",
        )
        assert result.user_id.value == "user-123"
        assert result.email.value == "test@example.com"
        assert result.display_name.value == "太郎"

    def test_既存ユーザーの登録でエラー(self):
        repo = InMemoryUserRepository()
        use_case = RegisterUserUseCase(repo)
        use_case.execute(
            user_id="user-123",
            email="test@example.com",
            display_name="太郎",
            date_of_birth_str="2000-01-01",
        )
        with pytest.raises(UserAlreadyExistsError):
            use_case.execute(
                user_id="user-123",
                email="other@example.com",
                display_name="花子",
                date_of_birth_str="2000-06-15",
            )

    def test_Google認証プロバイダで登録(self):
        repo = InMemoryUserRepository()
        use_case = RegisterUserUseCase(repo)
        result = use_case.execute(
            user_id="google-user-123",
            email="google@example.com",
            display_name="Googleユーザー",
            date_of_birth_str="1990-05-20",
            auth_provider="google",
        )
        assert result.user_id.value == "google-user-123"
