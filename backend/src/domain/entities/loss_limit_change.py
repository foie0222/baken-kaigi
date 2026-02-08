"""負け額限度額変更リクエストエンティティ."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..enums import LossLimitChangeStatus, LossLimitChangeType
from ..identifiers import LossLimitChangeId, UserId
from ..value_objects import Money


@dataclass
class LossLimitChange:
    """負け額限度額の変更リクエスト."""

    change_id: LossLimitChangeId
    user_id: UserId
    current_limit: Money
    requested_limit: Money
    change_type: LossLimitChangeType
    status: LossLimitChangeStatus
    effective_at: datetime
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        user_id: UserId,
        current_limit: Money,
        requested_limit: Money,
    ) -> LossLimitChange:
        """変更リクエストを作成する."""
        if current_limit == requested_limit:
            raise ValueError("Requested limit is the same as current limit")

        now = datetime.now(timezone.utc)

        if requested_limit.is_greater_than(current_limit):
            change_type = LossLimitChangeType.INCREASE
            status = LossLimitChangeStatus.PENDING
            effective_at = now + timedelta(days=7)
        else:
            change_type = LossLimitChangeType.DECREASE
            status = LossLimitChangeStatus.APPROVED
            effective_at = now

        return cls(
            change_id=LossLimitChangeId.generate(),
            user_id=user_id,
            current_limit=current_limit,
            requested_limit=requested_limit,
            change_type=change_type,
            status=status,
            effective_at=effective_at,
            requested_at=now,
        )

    def approve(self) -> None:
        """変更リクエストを承認する."""
        if self.status != LossLimitChangeStatus.PENDING:
            raise ValueError("Change is not pending")
        self.status = LossLimitChangeStatus.APPROVED

    def reject(self) -> None:
        """変更リクエストを却下する."""
        if self.status != LossLimitChangeStatus.PENDING:
            raise ValueError("Change is not pending")
        self.status = LossLimitChangeStatus.REJECTED

    def is_effective(self, now: datetime | None = None) -> bool:
        """変更が有効かどうか判定する."""
        if self.status != LossLimitChangeStatus.APPROVED:
            return False
        if now is None:
            now = datetime.now(timezone.utc)
        return now >= self.effective_at
