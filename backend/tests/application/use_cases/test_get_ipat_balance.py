"""GetIpatBalanceUseCase のテスト."""
import pytest

from src.application.use_cases.get_ipat_balance import (
    GetIpatBalanceUseCase,
    CredentialsNotFoundError,
)
from src.domain.identifiers import UserId
from src.domain.value_objects import IpatCredentials
from src.infrastructure.providers.in_memory_credentials_provider import (
    InMemoryCredentialsProvider,
)
from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway


class TestGetIpatBalanceUseCase:
    """GetIpatBalanceUseCase のテスト."""

    def test_正常取得(self) -> None:
        cred_provider = InMemoryCredentialsProvider()
        gateway = MockIpatGateway()
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                card_number="123456789012",
                birthday="19900101",
                pin="1234",
                dummy_pin="5678",
            ),
        )
        use_case = GetIpatBalanceUseCase(
            credentials_provider=cred_provider,
            ipat_gateway=gateway,
        )
        result = use_case.execute("user-001")
        assert result.bet_balance == 100000

    def test_認証情報なしでエラー(self) -> None:
        cred_provider = InMemoryCredentialsProvider()
        gateway = MockIpatGateway()
        use_case = GetIpatBalanceUseCase(
            credentials_provider=cred_provider,
            ipat_gateway=gateway,
        )
        with pytest.raises(CredentialsNotFoundError):
            use_case.execute("user-001")
