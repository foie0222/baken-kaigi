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
    create_uc.execute("usr_001", "ハヤテ", "solid")

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

    def test_エージェントの成績が更新される(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", _make_bets(hit=True))

        from src.domain.identifiers import UserId
        agent = agent_repo.find_by_user_id(UserId("usr_001"))
        assert agent.performance.total_bets == 1
        assert agent.performance.wins == 1
        assert agent.performance.total_invested == 1500
        assert agent.performance.total_return == 3000

    def test_エージェントのステータスが変化する(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        from src.domain.identifiers import UserId
        agent_before = agent_repo.find_by_user_id(UserId("usr_001"))
        rm_before = agent_before.stats.risk_management

        uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", _make_bets(hit=True))

        agent_after = agent_repo.find_by_user_id(UserId("usr_001"))
        # solidスタイルの的中ボーナス: risk_management +3 (基本1 + ボーナス2)
        assert agent_after.stats.risk_management == rm_before + 3

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

    def test_振り返りがリポジトリに保存される(self):
        agent_repo, review_repo = _setup()
        uc = CreateAgentReviewUseCase(agent_repo, review_repo)

        result = uc.execute("usr_001", "race_001", "2026-02-01", "東京11R", _make_bets())

        from src.domain.identifiers import UserId
        agent = agent_repo.find_by_user_id(UserId("usr_001"))
        reviews = review_repo.find_by_agent_id(agent.agent_id)
        assert len(reviews) == 1
        assert reviews[0].review_id == result.review.review_id

    def test_ステータス変化にスタイル別ボーナスが反映される(self):
        """各スタイルで的中時のボーナスが異なること."""
        for style, bonus_stat in [
            ("solid", "risk_management"),
            ("longshot", "intuition"),
            ("data", "data_analysis"),
            ("pace", "pace_reading"),
        ]:
            agent_repo = InMemoryAgentRepository()
            review_repo = InMemoryAgentReviewRepository()
            CreateAgentUseCase(agent_repo).execute(f"usr_{style}", "テスト", style)

            uc = CreateAgentReviewUseCase(agent_repo, review_repo)
            result = uc.execute(f"usr_{style}", "race_001", "2026-02-01", "テスト", _make_bets(hit=True))

            # ボーナスステータスは基本1 + ボーナス2 = 3
            assert result.review.stats_change[bonus_stat] == 3, f"{style}: {bonus_stat} should be 3"
