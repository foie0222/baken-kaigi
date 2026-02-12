"""エージェント振り返りエンティティ."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..identifiers import AgentId, RaceId, ReviewId


@dataclass(frozen=True)
class BetResult:
    """個別の賭け結果."""

    bet_type: str
    horse_numbers: list[int]
    amount: int
    result: str  # "hit" or "miss"
    payout: int


@dataclass
class AgentReview:
    """エージェントのレース振り返り."""

    review_id: ReviewId
    agent_id: AgentId
    race_id: RaceId
    race_date: str
    race_name: str
    bet_results: list[BetResult]
    total_invested: int
    total_return: int
    review_text: str
    learnings: list[str]
    stats_change: dict[str, int]  # e.g. {"data_analysis": 2}
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def profit(self) -> int:
        """収支."""
        return self.total_return - self.total_invested

    @property
    def has_win(self) -> bool:
        """的中があるかどうか."""
        return any(r.result == "hit" for r in self.bet_results)
