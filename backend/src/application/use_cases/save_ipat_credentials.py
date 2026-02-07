"""IPAT認証情報保存ユースケース."""
from src.domain.identifiers import UserId
from src.domain.ports import IpatCredentialsProvider
from src.domain.value_objects import IpatCredentials


class SaveIpatCredentialsUseCase:
    """IPAT認証情報保存ユースケース."""

    def __init__(self, credentials_provider: IpatCredentialsProvider) -> None:
        """初期化."""
        self._credentials_provider = credentials_provider

    def execute(
        self,
        user_id: str,
        card_number: str,
        birthday: str,
        pin: str,
        dummy_pin: str,
    ) -> None:
        """認証情報を保存する."""
        uid = UserId(user_id)
        credentials = IpatCredentials(
            card_number=card_number,
            birthday=birthday,
            pin=pin,
            dummy_pin=dummy_pin,
        )
        self._credentials_provider.save_credentials(uid, credentials)
