"""投票成績サマリーの値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .money import Money

if TYPE_CHECKING:
    from ..entities.betting_record import BettingRecord


@dataclass(frozen=True)
class BettingSummary:
    """投票成績のサマリー."""

    total_investment: Money
    total_payout: Money
    net_profit: int
    win_rate: float
    record_count: int
    roi: float

    @classmethod
    def from_records(cls, records: list[BettingRecord]) -> BettingSummary:
        """投票記録リストからサマリーを生成する."""
        if not records:
            return cls(
                total_investment=Money.zero(),
                total_payout=Money.zero(),
                net_profit=0,
                win_rate=0.0,
                record_count=0,
                roi=0.0,
            )

        total_investment = sum(r.amount.value for r in records)
        total_payout = sum(r.payout.value for r in records)
        net_profit = total_payout - total_investment
        win_count = sum(1 for r in records if r.payout.value > 0)
        record_count = len(records)
        win_rate = win_count / record_count if record_count > 0 else 0.0
        roi = (total_payout / total_investment * 100) if total_investment > 0 else 0.0

        return cls(
            total_investment=Money.of(total_investment),
            total_payout=Money.of(total_payout),
            net_profit=net_profit,
            win_rate=win_rate,
            record_count=record_count,
            roi=roi,
        )
