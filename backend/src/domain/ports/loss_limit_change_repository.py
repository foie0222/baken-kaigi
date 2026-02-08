"""負け額限度額変更リポジトリインターフェース."""
from abc import ABC, abstractmethod

from ..entities import LossLimitChange
from ..identifiers import LossLimitChangeId, UserId


class LossLimitChangeRepository(ABC):
    """負け額限度額変更リポジトリのインターフェース."""

    @abstractmethod
    def save(self, change: LossLimitChange) -> None:
        """変更リクエストを保存する."""
        pass

    @abstractmethod
    def find_by_id(self, change_id: LossLimitChangeId) -> LossLimitChange | None:
        """変更リクエストIDで検索する."""
        pass

    @abstractmethod
    def find_pending_by_user_id(self, user_id: UserId) -> list[LossLimitChange]:
        """ユーザーIDで保留中の変更リクエストを検索する."""
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: UserId) -> list[LossLimitChange]:
        """ユーザーIDで変更リクエストを検索する."""
        pass
