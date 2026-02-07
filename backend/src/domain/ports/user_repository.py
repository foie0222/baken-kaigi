"""ユーザーリポジトリインターフェース."""
from abc import ABC, abstractmethod

from ..entities import User
from ..identifiers import UserId
from ..value_objects import Email


class UserRepository(ABC):
    """ユーザーリポジトリのインターフェース."""

    @abstractmethod
    def save(self, user: User) -> None:
        """ユーザーを保存する."""
        pass

    @abstractmethod
    def find_by_id(self, user_id: UserId) -> User | None:
        """ユーザーIDで検索する."""
        pass

    @abstractmethod
    def find_by_email(self, email: Email) -> User | None:
        """メールアドレスで検索する."""
        pass

    @abstractmethod
    def delete(self, user_id: UserId) -> None:
        """ユーザーを削除する."""
        pass
