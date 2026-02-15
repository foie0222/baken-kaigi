"""エージェント作成ユースケース."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.domain.entities import Agent
from src.domain.identifiers import AgentId, UserId
from src.domain.ports.agent_repository import AgentRepository
from src.domain.value_objects import AgentName


class AgentAlreadyExistsError(Exception):
    """エージェントが既に存在するエラー."""

    pass


@dataclass(frozen=True)
class CreateAgentResult:
    """エージェント作成結果."""

    agent: Agent


class CreateAgentUseCase:
    """エージェント作成ユースケース."""

    def __init__(self, agent_repository: AgentRepository) -> None:
        """初期化."""
        self._agent_repository = agent_repository

    def execute(self, user_id: str, name: str) -> CreateAgentResult:
        """エージェントを作成する.

        Args:
            user_id: ユーザーID
            name: エージェント名

        Returns:
            作成結果

        Raises:
            AgentAlreadyExistsError: 既にエージェントが存在する場合
            ValueError: パラメータが不正な場合
        """
        uid = UserId(user_id)

        # 1人1体制約チェック
        existing = self._agent_repository.find_by_user_id(uid)
        if existing is not None:
            raise AgentAlreadyExistsError(f"Agent already exists for user: {user_id}")

        # 値オブジェクト変換
        agent_name = AgentName(name)
        agent_id = AgentId(f"agt_{uuid.uuid4().hex[:12]}")

        agent = Agent.create(
            agent_id=agent_id,
            user_id=uid,
            name=agent_name,
        )

        self._agent_repository.save(agent)

        return CreateAgentResult(agent=agent)
