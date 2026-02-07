"""GetPurchaseHistoryUseCase のテスト."""
from datetime import datetime

from src.application.use_cases.get_purchase_history import GetPurchaseHistoryUseCase
from src.domain.entities import PurchaseOrder
from src.domain.enums import IpatBetType, IpatVenueCode, PurchaseStatus
from src.domain.identifiers import CartId, PurchaseId, UserId
from src.domain.value_objects import IpatBetLine, Money
from src.infrastructure.repositories.in_memory_purchase_order_repository import (
    InMemoryPurchaseOrderRepository,
)


def _make_order(purchase_id: str = "p-001", user_id: str = "user-001") -> PurchaseOrder:
    return PurchaseOrder(
        id=PurchaseId(purchase_id),
        user_id=UserId(user_id),
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
        status=PurchaseStatus.COMPLETED,
        total_amount=Money.of(100),
        created_at=datetime(2026, 2, 7, 10, 0, 0),
        updated_at=datetime(2026, 2, 7, 10, 0, 0),
    )


class TestGetPurchaseHistoryUseCase:
    """GetPurchaseHistoryUseCase のテスト."""

    def test_取得成功(self) -> None:
        repo = InMemoryPurchaseOrderRepository()
        repo.save(_make_order("p-001"))
        repo.save(_make_order("p-002"))
        use_case = GetPurchaseHistoryUseCase(purchase_order_repository=repo)
        results = use_case.execute("user-001")
        assert len(results) == 2

    def test_注文なしで空リスト(self) -> None:
        repo = InMemoryPurchaseOrderRepository()
        use_case = GetPurchaseHistoryUseCase(purchase_order_repository=repo)
        results = use_case.execute("user-001")
        assert results == []
