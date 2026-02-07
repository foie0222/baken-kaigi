"""購入履歴取得ユースケース."""
from src.domain.entities import PurchaseOrder
from src.domain.identifiers import UserId
from src.domain.ports import PurchaseOrderRepository


class GetPurchaseHistoryUseCase:
    """購入履歴取得ユースケース."""

    def __init__(self, purchase_order_repository: PurchaseOrderRepository) -> None:
        """初期化."""
        self._purchase_order_repository = purchase_order_repository

    def execute(self, user_id: str) -> list[PurchaseOrder]:
        """購入履歴を取得する."""
        uid = UserId(user_id)
        return self._purchase_order_repository.find_by_user_id(uid)
