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
            inet_id="ABcd1234",
            subscriber_number="12345678",
            pin="1234",
            pars_number="5678",
        )
        assert provider.has_credentials(UserId("user-001")) is True

    def test_バリデーションエラー_INET_ID不正(self) -> None:
        provider = InMemoryCredentialsProvider()
        use_case = SaveIpatCredentialsUseCase(credentials_provider=provider)
        with pytest.raises(ValueError):
            use_case.execute(
                user_id="user-001",
                inet_id="invalid",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            )
