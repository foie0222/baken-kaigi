"""IPAT認証情報削除ユースケース."""
from src.domain.identifiers import UserId
from src.domain.ports import IpatCredentialsProvider


class DeleteIpatCredentialsUseCase:
    """IPAT認証情報削除ユースケース."""

    def __init__(self, credentials_provider: IpatCredentialsProvider) -> None:
        """初期化."""
        self._credentials_provider = credentials_provider

    def execute(self, user_id: str) -> None:
        """認証情報を削除する."""
        uid = UserId(user_id)
        self._credentials_provider.delete_credentials(uid)
