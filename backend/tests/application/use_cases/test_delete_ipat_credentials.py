"""DeleteIpatCredentialsUseCase のテスト."""
from src.application.use_cases.delete_ipat_credentials import DeleteIpatCredentialsUseCase
from src.domain.identifiers import UserId
from src.domain.value_objects import IpatCredentials
from src.infrastructure.providers.in_memory_credentials_provider import (
    InMemoryCredentialsProvider,
)


class TestDeleteIpatCredentialsUseCase:
    """DeleteIpatCredentialsUseCase のテスト."""

    def test_削除成功(self) -> None:
        provider = InMemoryCredentialsProvider()
        provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            ),
        )
        use_case = DeleteIpatCredentialsUseCase(credentials_provider=provider)
        use_case.execute("user-001")
        assert provider.has_credentials(UserId("user-001")) is False
