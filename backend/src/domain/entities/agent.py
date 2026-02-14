"""エージェントエンティティ."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..enums import AgentStyle
from ..identifiers import AgentId, UserId
from ..value_objects import AgentName, AgentPerformance, BettingPreference

# レベル算出用の経験値閾値
_LEVEL_THRESHOLDS = [0, 10, 30, 60, 100, 150, 210, 280, 360, 450]


@dataclass
class Agent:
    """競馬予想エージェント（集約ルート）."""

    agent_id: AgentId
    user_id: UserId
    name: AgentName
    base_style: AgentStyle
    performance: AgentPerformance = field(default_factory=AgentPerformance.empty)
    betting_preference: BettingPreference = field(default_factory=BettingPreference.default)
    custom_instructions: str | None = None
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
            performance=AgentPerformance.empty(),
            betting_preference=BettingPreference.default(),
            custom_instructions=None,
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

    def update_style(self, style: AgentStyle) -> None:
        """分析スタイルを変更する."""
        self.base_style = style
        self.updated_at = datetime.now(timezone.utc)

    def update_preference(self, preference: BettingPreference, custom_instructions: str | None) -> None:
        """好み設定を更新する."""
        if custom_instructions is not None and len(custom_instructions) > 200:
            raise ValueError("custom_instructionsは200文字以内にしてください")
        self.betting_preference = preference
        self.custom_instructions = custom_instructions
        self.updated_at = datetime.now(timezone.utc)

    def record_result(self, invested: int, returned: int, is_win: bool) -> None:
        """レース結果を記録する."""
        self.performance = self.performance.record_result(invested, returned, is_win)
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
