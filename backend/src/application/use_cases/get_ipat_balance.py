"""IPAT残高取得ユースケース."""
from src.domain.identifiers import UserId
from src.domain.ports import IpatCredentialsProvider, IpatGateway
from src.domain.value_objects import IpatBalance


class CredentialsNotFoundError(Exception):
    """IPAT認証情報が見つからないエラー."""

    pass


class GetIpatBalanceUseCase:
    """IPAT残高取得ユースケース."""

    def __init__(
        self,
        credentials_provider: IpatCredentialsProvider,
        ipat_gateway: IpatGateway,
    ) -> None:
        """初期化."""
        self._credentials_provider = credentials_provider
        self._ipat_gateway = ipat_gateway

    def execute(self, user_id: str) -> IpatBalance:
        """残高を取得する."""
        uid = UserId(user_id)
        credentials = self._credentials_provider.get_credentials(uid)
        if credentials is None:
            raise CredentialsNotFoundError("IPAT credentials not configured")

        return self._ipat_gateway.get_balance(credentials)
