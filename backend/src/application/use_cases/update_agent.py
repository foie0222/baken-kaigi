"""エージェント更新ユースケース."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import Agent
from src.domain.enums import AgentStyle
from src.domain.identifiers import UserId
from src.domain.ports.agent_repository import AgentRepository

from .get_agent import AgentNotFoundError


@dataclass(frozen=True)
class UpdateAgentResult:
    """エージェント更新結果."""

    agent: Agent


class UpdateAgentUseCase:
    """エージェント更新ユースケース."""

    def __init__(self, agent_repository: AgentRepository) -> None:
        """初期化."""
        self._agent_repository = agent_repository

    def execute(self, user_id: str, base_style: str | None = None) -> UpdateAgentResult:
        """エージェントを更新する.

        Args:
            user_id: ユーザーID
            base_style: 新しいスタイル（solid/longshot/data/pace）

        Returns:
            更新結果

        Raises:
            AgentNotFoundError: エージェントが見つからない場合
            ValueError: パラメータが不正な場合
        """
        uid = UserId(user_id)
        agent = self._agent_repository.find_by_user_id(uid)

        if agent is None:
            raise AgentNotFoundError(f"Agent not found for user: {user_id}")

        if base_style is not None:
            agent.update_style(AgentStyle(base_style))

        self._agent_repository.save(agent)

        return UpdateAgentResult(agent=agent)
