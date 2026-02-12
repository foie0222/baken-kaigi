"""エージェントエンティティ."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..enums import AgentStyle
from ..identifiers import AgentId, UserId
from ..value_objects import AgentName, AgentPerformance, AgentStats

# レベル算出用の経験値閾値
_LEVEL_THRESHOLDS = [0, 10, 30, 60, 100, 150, 210, 280, 360, 450]


@dataclass
class Agent:
    """競馬予想エージェント（集約ルート）."""

    agent_id: AgentId
    user_id: UserId
    name: AgentName
    base_style: AgentStyle
    stats: AgentStats
    performance: AgentPerformance = field(default_factory=AgentPerformance.empty)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        agent_id: AgentId,
        user_id: UserId,
        name: AgentName,
        base_style: AgentStyle,
    ) -> Agent:
        """新しいエージェントを作成する."""
        now = datetime.now(timezone.utc)
        return cls(
            agent_id=agent_id,
            user_id=user_id,
            name=name,
            base_style=base_style,
            stats=AgentStats.initial_for_style(base_style.value),
            performance=AgentPerformance.empty(),
            created_at=now,
            updated_at=now,
        )

    @property
    def level(self) -> int:
        """現在のレベルを算出する（total_bets基準）."""
        bets = self.performance.total_bets
        level = 1
        for i, threshold in enumerate(_LEVEL_THRESHOLDS):
            if bets >= threshold:
                level = i + 1
            else:
                break
        return level

    def update_name(self, name: AgentName) -> None:
        """エージェント名を変更する."""
        self.name = name
        self.updated_at = datetime.now(timezone.utc)

    def record_result(self, invested: int, returned: int, is_win: bool) -> None:
        """レース結果を記録する."""
        self.performance = self.performance.record_result(invested, returned, is_win)
        self.updated_at = datetime.now(timezone.utc)

    def apply_stats_change(
        self,
        data_analysis: int = 0,
        pace_reading: int = 0,
        risk_management: int = 0,
        intuition: int = 0,
    ) -> None:
        """能力値を変更する."""
        self.stats = self.stats.apply_change(
            data_analysis=data_analysis,
            pace_reading=pace_reading,
            risk_management=risk_management,
            intuition=intuition,
        )
        self.updated_at = datetime.now(timezone.utc)

    def to_character_type(self) -> str:
        """既存のcharacter_typeに変換する（互換性維持）."""
        mapping = {
            AgentStyle.SOLID: "conservative",
            AgentStyle.LONGSHOT: "intuition",
            AgentStyle.DATA: "analyst",
            AgentStyle.PACE: "aggressive",
        }
        return mapping[self.base_style]
