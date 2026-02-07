"""購入注文リポジトリインターフェース."""
from abc import ABC, abstractmethod

from ..entities import PurchaseOrder
from ..identifiers import PurchaseId, UserId


class PurchaseOrderRepository(ABC):
    """購入注文リポジトリのインターフェース."""

    @abstractmethod
    def save(self, order: PurchaseOrder) -> None:
        """購入注文を保存する."""
        pass

    @abstractmethod
    def find_by_id(self, purchase_id: PurchaseId) -> PurchaseOrder | None:
        """購入注文IDで検索する."""
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: UserId) -> list[PurchaseOrder]:
        """ユーザーIDで検索する."""
        pass
