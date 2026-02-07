"""IPAT認証情報プロバイダーインターフェース."""
from abc import ABC, abstractmethod

from ..identifiers import UserId
from ..value_objects import IpatCredentials


class IpatCredentialsProvider(ABC):
    """IPAT認証情報の管理インターフェース."""

    @abstractmethod
    def get_credentials(self, user_id: UserId) -> IpatCredentials | None:
        """ユーザーのIPAT認証情報を取得する."""
        pass

    @abstractmethod
    def save_credentials(self, user_id: UserId, credentials: IpatCredentials) -> None:
        """ユーザーのIPAT認証情報を保存する."""
        pass

    @abstractmethod
    def delete_credentials(self, user_id: UserId) -> None:
        """ユーザーのIPAT認証情報を削除する."""
        pass

    @abstractmethod
    def has_credentials(self, user_id: UserId) -> bool:
        """ユーザーがIPAT認証情報を持っているか判定する."""
        pass
