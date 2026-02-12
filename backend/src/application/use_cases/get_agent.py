"""エージェント取得ユースケース."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import Agent
from src.domain.identifiers import UserId
from src.domain.ports.agent_repository import AgentRepository


class AgentNotFoundError(Exception):
    """エージェントが見つからないエラー."""

    pass


@dataclass(frozen=True)
class GetAgentResult:
    """エージェント取得結果."""

    agent: Agent


class GetAgentUseCase:
    """エージェント取得ユースケース."""

    def __init__(self, agent_repository: AgentRepository) -> None:
        """初期化."""
        self._agent_repository = agent_repository

    def execute(self, user_id: str) -> GetAgentResult:
        """ユーザーのエージェントを取得する.

        Args:
            user_id: ユーザーID

        Returns:
            取得結果

        Raises:
            AgentNotFoundError: エージェントが見つからない場合
        """
        uid = UserId(user_id)
        agent = self._agent_repository.find_by_user_id(uid)

        if agent is None:
            raise AgentNotFoundError(f"Agent not found for user: {user_id}")

        return GetAgentResult(agent=agent)
