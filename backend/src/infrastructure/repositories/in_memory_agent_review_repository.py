"""インメモリエージェント振り返りリポジトリ実装."""
from src.domain.entities import AgentReview
from src.domain.identifiers import AgentId, ReviewId
from src.domain.ports.agent_review_repository import AgentReviewRepository


class InMemoryAgentReviewRepository(AgentReviewRepository):
    """インメモリエージェント振り返りリポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._reviews: dict[str, AgentReview] = {}

    def save(self, review: AgentReview) -> None:
        """振り返りを保存する."""
        self._reviews[review.review_id.value] = review

    def find_by_id(self, review_id: ReviewId) -> AgentReview | None:
        """振り返りIDで検索する."""
        return self._reviews.get(review_id.value)

    def find_by_agent_id(self, agent_id: AgentId, limit: int = 20) -> list[AgentReview]:
        """エージェントIDで振り返り一覧を取得する（新しい順）."""
        reviews = [
            r for r in self._reviews.values() if r.agent_id.value == agent_id.value
        ]
        reviews.sort(key=lambda r: r.created_at, reverse=True)
        return reviews[:limit]
