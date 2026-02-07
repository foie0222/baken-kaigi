"""InMemoryPurchaseOrderRepository のテスト."""
import unittest
from datetime import datetime

from src.domain.entities import PurchaseOrder
from src.domain.enums import IpatBetType, IpatVenueCode, PurchaseStatus
from src.domain.identifiers import CartId, PurchaseId, UserId
from src.domain.value_objects import IpatBetLine, Money
from src.infrastructure.repositories.in_memory_purchase_order_repository import (
    InMemoryPurchaseOrderRepository,
)


class TestInMemoryPurchaseOrderRepository(unittest.TestCase):
    """InMemoryPurchaseOrderRepository のテスト."""

    def setUp(self) -> None:
        self.repo = InMemoryPurchaseOrderRepository()
        self.user_id = UserId("user-001")
        self.order = self._make_order()

    def _make_order(
        self,
        purchase_id: str = "purchase-001",
        user_id: str | None = None,
    ) -> PurchaseOrder:
        uid = UserId(user_id) if user_id else self.user_id
        return PurchaseOrder(
            id=PurchaseId(purchase_id),
            user_id=uid,
            cart_id=CartId("cart-001"),
            bet_lines=[
                IpatBetLine(
                    opdt="20260207",
                    venue_code=IpatVenueCode.TOKYO,
                    race_number=11,
                    bet_type=IpatBetType.TANSYO,
                    number="01",
                    amount=100,
                ),
            ],
            status=PurchaseStatus.PENDING,
            total_amount=Money.of(100),
            created_at=datetime(2026, 2, 7, 10, 0, 0),
            updated_at=datetime(2026, 2, 7, 10, 0, 0),
        )

    def test_保存と取得(self) -> None:
        self.repo.save(self.order)
        result = self.repo.find_by_id(PurchaseId("purchase-001"))
        assert result is not None
        assert result.id.value == "purchase-001"

    def test_存在しないIDで検索するとNone(self) -> None:
        result = self.repo.find_by_id(PurchaseId("not-exist"))
        assert result is None

    def test_ユーザーIDで検索(self) -> None:
        self.repo.save(self.order)
        order2 = self._make_order(purchase_id="purchase-002")
        self.repo.save(order2)

        results = self.repo.find_by_user_id(self.user_id)
        assert len(results) == 2

    def test_別ユーザーの注文は返さない(self) -> None:
        self.repo.save(self.order)
        other_order = self._make_order(purchase_id="purchase-003", user_id="user-other")
        self.repo.save(other_order)

        results = self.repo.find_by_user_id(self.user_id)
        assert len(results) == 1
        assert results[0].id.value == "purchase-001"

    def test_ユーザーIDで検索_注文なしで空リスト(self) -> None:
        results = self.repo.find_by_user_id(UserId("no-orders"))
        assert results == []

    def test_保存で既存注文を上書き(self) -> None:
        self.repo.save(self.order)
        self.order.mark_completed()
        self.repo.save(self.order)

        result = self.repo.find_by_id(PurchaseId("purchase-001"))
        assert result is not None
        assert result.status == PurchaseStatus.COMPLETED
