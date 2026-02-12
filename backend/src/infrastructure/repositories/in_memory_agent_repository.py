"""インメモリエージェントリポジトリ実装."""
from src.domain.entities import Agent
from src.domain.identifiers import AgentId, UserId
from src.domain.ports.agent_repository import AgentRepository


class InMemoryAgentRepository(AgentRepository):
    """インメモリエージェントリポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._agents: dict[str, Agent] = {}

    def save(self, agent: Agent) -> None:
        """エージェントを保存する."""
        self._agents[agent.agent_id.value] = agent

    def find_by_id(self, agent_id: AgentId) -> Agent | None:
        """エージェントIDで検索する."""
        return self._agents.get(agent_id.value)

    def find_by_user_id(self, user_id: UserId) -> Agent | None:
        """ユーザーIDでエージェントを検索する."""
        for agent in self._agents.values():
            if agent.user_id.value == user_id.value:
                return agent
        return None

    def delete(self, agent_id: AgentId) -> None:
        """エージェントを削除する."""
        self._agents.pop(agent_id.value, None)
