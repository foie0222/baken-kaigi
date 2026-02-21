"""エージェント振り返りリポジトリインターフェース."""
from abc import ABC, abstractmethod

from ..entities import AgentReview
from ..identifiers import AgentId, RaceId, ReviewId


class AgentReviewRepository(ABC):
    """エージェント振り返りリポジトリのインターフェース."""

    @abstractmethod
    def save(self, review: AgentReview) -> None:
        """振り返りを保存する."""
        pass

    @abstractmethod
    def find_by_id(self, review_id: ReviewId) -> AgentReview | None:
        """振り返りIDで検索する."""
        pass

    @abstractmethod
    def find_by_agent_id(self, agent_id: AgentId, limit: int = 20) -> list[AgentReview]:
        """エージェントIDで振り返り一覧を取得する（新しい順）."""
        pass

    @abstractmethod
    def exists_by_agent_and_race(self, agent_id: AgentId, race_id: RaceId) -> bool:
        """指定エージェント・レースの振り返りが存在するか判定する."""
        pass
