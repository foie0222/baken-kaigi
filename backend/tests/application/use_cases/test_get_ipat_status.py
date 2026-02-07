"""GetIpatStatusUseCase のテスト."""
from src.application.use_cases.get_ipat_status import GetIpatStatusUseCase
from src.domain.identifiers import UserId
from src.domain.value_objects import IpatCredentials
from src.infrastructure.providers.in_memory_credentials_provider import (
    InMemoryCredentialsProvider,
)


class TestGetIpatStatusUseCase:
    """GetIpatStatusUseCase のテスト."""

    def test_設定済み(self) -> None:
        provider = InMemoryCredentialsProvider()
        provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                card_number="123456789012",
                birthday="19900101",
                pin="1234",
                dummy_pin="5678",
            ),
        )
        use_case = GetIpatStatusUseCase(credentials_provider=provider)
        result = use_case.execute("user-001")
        assert result == {"configured": True}

    def test_未設定(self) -> None:
        provider = InMemoryCredentialsProvider()
        use_case = GetIpatStatusUseCase(credentials_provider=provider)
        result = use_case.execute("user-001")
        assert result == {"configured": False}
