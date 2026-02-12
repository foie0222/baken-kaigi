"""エージェント通算成績の値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPerformance:
    """エージェントの通算成績."""

    total_bets: int  # 総投票数
    wins: int  # 的中数
    total_invested: int  # 総投資額（円）
    total_return: int  # 総回収額（円）

    def __post_init__(self) -> None:
        """バリデーション."""
        if self.total_bets < 0:
            raise ValueError("total_bets cannot be negative")
        if self.wins < 0:
            raise ValueError("wins cannot be negative")
        if self.wins > self.total_bets:
            raise ValueError("wins cannot exceed total_bets")
        if self.total_invested < 0:
            raise ValueError("total_invested cannot be negative")
        if self.total_return < 0:
            raise ValueError("total_return cannot be negative")

    @classmethod
    def empty(cls) -> AgentPerformance:
        """空の成績を生成する."""
        return cls(total_bets=0, wins=0, total_invested=0, total_return=0)

    @property
    def win_rate(self) -> float:
        """的中率（0.0〜1.0）."""
        if self.total_bets == 0:
            return 0.0
        return self.wins / self.total_bets

    @property
    def roi(self) -> float:
        """回収率（0.0〜、1.0 = 100%）."""
        if self.total_invested == 0:
            return 0.0
        return self.total_return / self.total_invested

    @property
    def profit(self) -> int:
        """収支（円）."""
        return self.total_return - self.total_invested

    def record_result(self, invested: int, returned: int, is_win: bool) -> AgentPerformance:
        """結果を記録した新しいAgentPerformanceを返す."""
        return AgentPerformance(
            total_bets=self.total_bets + 1,
            wins=self.wins + (1 if is_win else 0),
            total_invested=self.total_invested + invested,
            total_return=self.total_return + returned,
        )

    def to_dict(self) -> dict:
        """辞書に変換する."""
        return {
            "total_bets": self.total_bets,
            "wins": self.wins,
            "total_invested": self.total_invested,
            "total_return": self.total_return,
        }
