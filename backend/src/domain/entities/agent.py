"""エージェントエンティティ."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..identifiers import AgentId, UserId
from ..value_objects import AgentName, BettingPreference


@dataclass
class Agent:
    """競馬予想エージェント（集約ルート）."""

    agent_id: AgentId
    user_id: UserId
    name: AgentName
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
    ) -> Agent:
        """新しいエージェントを作成する."""
        now = datetime.now(timezone.utc)
        return cls(
            agent_id=agent_id,
            user_id=user_id,
            name=name,
            betting_preference=BettingPreference.default(),
            custom_instructions=None,
            created_at=now,
            updated_at=now,
        )

    def update_preference(self, preference: BettingPreference, custom_instructions: str | None) -> None:
        """好み設定を更新する."""
        if custom_instructions is not None and len(custom_instructions) > 200:
            raise ValueError("custom_instructionsは200文字以内にしてください")
        self.betting_preference = preference
        self.custom_instructions = custom_instructions
        self.updated_at = datetime.now(timezone.utc)
