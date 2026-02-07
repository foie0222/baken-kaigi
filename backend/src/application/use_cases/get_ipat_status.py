"""IPATステータス取得ユースケース."""
from src.domain.identifiers import UserId
from src.domain.ports import IpatCredentialsProvider


class GetIpatStatusUseCase:
    """IPATステータス取得ユースケース."""

    def __init__(self, credentials_provider: IpatCredentialsProvider) -> None:
        """初期化."""
        self._credentials_provider = credentials_provider

    def execute(self, user_id: str) -> dict:
        """IPAT設定ステータスを返す."""
        uid = UserId(user_id)
        return {"configured": self._credentials_provider.has_credentials(uid)}
