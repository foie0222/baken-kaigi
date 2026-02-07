"""IPAT認証情報プロバイダーのインメモリ実装."""
from src.domain.identifiers import UserId
from src.domain.ports import IpatCredentialsProvider
from src.domain.value_objects import IpatCredentials


class InMemoryCredentialsProvider(IpatCredentialsProvider):
    """IPAT認証情報プロバイダーのインメモリ実装（テスト用）."""

    def __init__(self) -> None:
        """初期化."""
        self._credentials: dict[str, IpatCredentials] = {}

    def get_credentials(self, user_id: UserId) -> IpatCredentials | None:
        """ユーザーのIPAT認証情報を取得する."""
        return self._credentials.get(user_id.value)

    def save_credentials(self, user_id: UserId, credentials: IpatCredentials) -> None:
        """ユーザーのIPAT認証情報を保存する."""
        self._credentials[user_id.value] = credentials

    def delete_credentials(self, user_id: UserId) -> None:
        """ユーザーのIPAT認証情報を削除する."""
        self._credentials.pop(user_id.value, None)

    def has_credentials(self, user_id: UserId) -> bool:
        """ユーザーがIPAT認証情報を持っているか判定する."""
        return user_id.value in self._credentials
