"""SaveIpatCredentialsUseCase のテスト."""
import pytest

from src.application.use_cases.save_ipat_credentials import SaveIpatCredentialsUseCase
from src.domain.identifiers import UserId
from src.infrastructure.providers.in_memory_credentials_provider import (
    InMemoryCredentialsProvider,
)


class TestSaveIpatCredentialsUseCase:
    """SaveIpatCredentialsUseCase のテスト."""

    def test_保存成功(self) -> None:
        provider = InMemoryCredentialsProvider()
        use_case = SaveIpatCredentialsUseCase(credentials_provider=provider)
        use_case.execute(
            user_id="user-001",
            card_number="123456789012",
            birthday="19900101",
            pin="1234",
            dummy_pin="5678",
        )
        assert provider.has_credentials(UserId("user-001")) is True

    def test_バリデーションエラー_カード番号不正(self) -> None:
        provider = InMemoryCredentialsProvider()
        use_case = SaveIpatCredentialsUseCase(credentials_provider=provider)
        with pytest.raises(ValueError):
            use_case.execute(
                user_id="user-001",
                card_number="invalid",
                birthday="19900101",
                pin="1234",
                dummy_pin="5678",
            )
