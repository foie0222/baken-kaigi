"""エージェント振り返りユースケースのテスト."""
import pytest

from src.application.use_cases import (
    AgentNotFoundError,
    CreateAgentReviewUseCase,
    CreateAgentUseCase,
    ReviewAlreadyExistsError,
)
from src.infrastructure.repositories.in_memory_agent_repository import InMemoryAgentRepository
from src.infrastructure.repositories.in_memory_agent_review_repository import InMemoryAgentReviewRepository


def _setup():
    """共通セットアップ: リポジトリとエージェントを作成する."""
    agent_repo = InMemoryAgentRepository()
    review_repo = InMemoryAgentReviewRepository()

    # エージェントを先に作成
    create_uc = CreateAgentUseCase(agent_repo)
    create_uc.execute("usr_001", "ハヤテ")

    return agent_repo, review_repo


def _make_bets(hit=True):
    """テスト用の賭け結果リストを生成する."""
    if hit:
        return [
            {"bet_type": "win", "horse_numbers": [3], "amount": 1000, "result": "hit", "payout": 3000},
            {"bet_type": "place", "horse_numbers": [5], "amount": 500, "result": "miss", "payout": 0},
        ]
    return [
        {"bet_type": "win", "horse_numbers": [3], "amount": 1000, "result": "miss", "payout": 0},
        {"bet_type": "place", "horse_numbers": [5], "amount": 500, "result": "miss", "payout": 0},
    ]


class TestCreateAgentReviewUseCase:
    """振り返り生成ユースケースのテスト."""

    def test_的中ありの振り返りを生成できる(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        result = uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", _make_bets(hit=True))

        assert result.review.race_name == "東京11R"
        assert result.review.total_invested == 1500
        assert result.review.total_return == 3000
        assert result.review.profit == 1500
        assert result.review.has_win is True
        assert "的中" in result.review.review_text
        assert len(result.review.learnings) > 0
        assert result.review.review_id.value.startswith("rev_")

    def test_不的中の振り返りを生成できる(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        result = uc.execute("usr_001", "race_002", "2026-02-01", "中山9R", _make_bets(hit=False))

        assert result.review.total_invested == 1500
        assert result.review.total_return == 0
        assert result.review.has_win is False
        assert "不的中" in result.review.review_text

    def test_同一レースの振り返り重複はエラー(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", _make_bets(hit=True))

        with pytest.raises(ReviewAlreadyExistsError):
            uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", _make_bets(hit=False))

    def test_存在しないユーザーはエラー(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        with pytest.raises(AgentNotFoundError):
            uc.execute("usr_nonexistent", "race_001", "2026-02-01", "東京11R", _make_bets())

    def test_空の賭け結果はエラー(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        with pytest.raises(ValueError):
            uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", [])

    def test_トリガミの振り返りテキスト(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        # 的中だが投資を下回る
        bets = [
            {"bet_type": "quinella", "horse_numbers": [3, 5], "amount": 1000, "result": "hit", "payout": 800},
        ]
        result = uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", bets)

        assert result.review.has_win is True
        assert result.review.profit == -200
        assert "絞り込む" in result.review.review_text

    def test_21件以上のレビューがあっても重複チェックが機能する(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        # 21件の異なるレースで振り返りを作成
        for i in range(21):
            uc.execute("usr_001", f"race_{i:03d}", "2026-02-01", f"レース{i}", _make_bets())

        # 最初のレース(race_000)の重複作成を試みる → エラーになるべき
        with pytest.raises(ReviewAlreadyExistsError):
            uc.execute("usr_001", "race_000", "2026-02-01", "レース0", _make_bets())

    def test_振り返りがリポジトリに保存される(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        result = uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", _make_bets())

        from src.domain.identifiers import UserId
        agent = agent_repo.find_by_user_id(UserId("usr_001"))
        reviews = review_repo.find_by_agent_id(agent.agent_id)
        assert len(reviews) == 1
        assert reviews[0].review_id == result.review.review_id

