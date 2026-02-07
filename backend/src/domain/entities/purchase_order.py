"""購入注文エンティティ."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..enums import PurchaseStatus
from ..identifiers import CartId, PurchaseId, UserId
from ..value_objects import IpatBetLine, Money


@dataclass
class PurchaseOrder:
    """IPAT購入注文."""

    id: PurchaseId
    user_id: UserId
    cart_id: CartId
    bet_lines: list[IpatBetLine]
    status: PurchaseStatus
    total_amount: Money
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    @classmethod
    def create(
        cls,
        user_id: UserId,
        cart_id: CartId,
        bet_lines: list[IpatBetLine],
        total_amount: Money,
    ) -> PurchaseOrder:
        """新しい購入注文を作成する."""
        now = datetime.now()
        return cls(
            id=PurchaseId.generate(),
            user_id=user_id,
            cart_id=cart_id,
            bet_lines=bet_lines,
            status=PurchaseStatus.PENDING,
            total_amount=total_amount,
            created_at=now,
            updated_at=now,
        )

    def mark_submitted(self) -> None:
        """投票送信済みに変更する."""
        self.status = PurchaseStatus.SUBMITTED
        self.updated_at = datetime.now()

    def mark_completed(self) -> None:
        """投票完了に変更する."""
        self.status = PurchaseStatus.COMPLETED
        self.updated_at = datetime.now()

    def mark_failed(self, error_message: str) -> None:
        """投票失敗に変更する."""
        self.status = PurchaseStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now()
