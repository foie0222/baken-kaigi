"""購入注文リポジトリのインメモリ実装."""
from src.domain.entities import PurchaseOrder
from src.domain.identifiers import PurchaseId, UserId
from src.domain.ports import PurchaseOrderRepository


class InMemoryPurchaseOrderRepository(PurchaseOrderRepository):
    """購入注文リポジトリのインメモリ実装."""

    def __init__(self) -> None:
        """初期化."""
        self._orders: dict[str, PurchaseOrder] = {}

    def save(self, order: PurchaseOrder) -> None:
        """購入注文を保存する."""
        self._orders[order.id.value] = order

    def find_by_id(self, purchase_id: PurchaseId) -> PurchaseOrder | None:
        """購入注文IDで検索する."""
        return self._orders.get(purchase_id.value)

    def find_by_user_id(self, user_id: UserId) -> list[PurchaseOrder]:
        """ユーザーIDで検索する."""
        return [
            order for order in self._orders.values()
            if order.user_id == user_id
        ]
