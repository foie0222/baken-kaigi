"""投票記録エンティティ."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from ..enums import BetType, BettingRecordStatus
from ..identifiers import BettingRecordId, RaceId, UserId
from ..value_objects import HorseNumbers, Money


@dataclass
class BettingRecord:
    """投票記録."""

    record_id: BettingRecordId
    user_id: UserId
    race_id: RaceId
    race_name: str
    race_date: date
    venue: str
    bet_type: BetType
    horse_numbers: HorseNumbers
    amount: Money
    payout: Money
    profit: int
    status: BettingRecordStatus
    created_at: datetime
    settled_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        user_id: UserId,
        race_id: RaceId,
        race_name: str,
        race_date: date,
        venue: str,
        bet_type: BetType,
        horse_numbers: HorseNumbers,
        amount: Money,
    ) -> BettingRecord:
        """新しい投票記録を作成する."""
        return cls(
            record_id=BettingRecordId.generate(),
            user_id=user_id,
            race_id=race_id,
            race_name=race_name,
            race_date=race_date,
            venue=venue,
            bet_type=bet_type,
            horse_numbers=horse_numbers,
            amount=amount,
            payout=Money.zero(),
            profit=0,
            status=BettingRecordStatus.PENDING,
            created_at=datetime.now(),
        )

    def settle(self, payout: Money) -> None:
        """レース確定後に払戻額を設定して確定する."""
        if self.status != BettingRecordStatus.PENDING:
            raise ValueError("settle can only be called on PENDING records")
        self.status = BettingRecordStatus.SETTLED
        self.payout = payout
        self.profit = payout.value - self.amount.value
        self.settled_at = datetime.now()

    def cancel(self) -> None:
        """投票を取り消す."""
        if self.status != BettingRecordStatus.PENDING:
            raise ValueError("cancel can only be called on PENDING records")
        self.status = BettingRecordStatus.CANCELLED
