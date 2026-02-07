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
        inet_id: str,
        subscriber_number: str,
        pin: str,
        pars_number: str,
    ) -> None:
        """認証情報を保存する."""
        uid = UserId(user_id)
        credentials = IpatCredentials(
            inet_id=inet_id,
            subscriber_number=subscriber_number,
            pin=pin,
            pars_number=pars_number,
        )
        self._credentials_provider.save_credentials(uid, credentials)
