"""エージェントリポジトリインターフェース."""
from abc import ABC, abstractmethod

from ..entities import Agent
from ..identifiers import AgentId, UserId


class AgentRepository(ABC):
    """エージェントリポジトリのインターフェース."""

    @abstractmethod
    def save(self, agent: Agent) -> None:
        """エージェントを保存する."""
        pass

    @abstractmethod
    def find_by_id(self, agent_id: AgentId) -> Agent | None:
        """エージェントIDで検索する."""
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: UserId) -> Agent | None:
        """ユーザーIDでエージェントを検索する（1人1体）."""
        pass

    @abstractmethod
    def delete(self, agent_id: AgentId) -> None:
        """エージェントを削除する."""
        pass
