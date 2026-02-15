"""エージェントエンティティのテスト."""
import pytest

from src.domain.entities import Agent
from src.domain.enums import AgentStyle, BetTypePreference
from src.domain.identifiers import AgentId, UserId
from src.domain.value_objects import AgentName, AgentPerformance, BettingPreference


class TestAgent:
    """Agentエンティティのテスト."""

    def test_エージェントを作成できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        assert agent.name.value == "ハヤテ"
        assert agent.base_style == AgentStyle.SOLID
        assert agent.performance.total_bets == 0
        assert agent.level == 1

    def test_レベルはtotal_betsで算出される(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.DATA,
        )
        # 0 bets → level 1
        assert agent.level == 1

        # 10 bets → level 2
        agent.performance = AgentPerformance(total_bets=10, wins=3, total_invested=10000, total_return=8000)
        assert agent.level == 2

        # 30 bets → level 3
        agent.performance = AgentPerformance(total_bets=30, wins=10, total_invested=30000, total_return=25000)
        assert agent.level == 3

        # 100 bets → level 5
        agent.performance = AgentPerformance(total_bets=100, wins=33, total_invested=100000, total_return=90000)
        assert agent.level == 5

    def test_結果を記録できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.LONGSHOT,
        )
        agent.record_result(invested=1000, returned=2400, is_win=True)
        assert agent.performance.total_bets == 1
        assert agent.performance.wins == 1
        assert agent.performance.total_invested == 1000
        assert agent.performance.total_return == 2400

    def test_スタイルを変更できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        agent.update_style(AgentStyle.DATA)
        assert agent.base_style == AgentStyle.DATA

    def test_character_typeへの変換(self):
        mapping = {
            AgentStyle.SOLID: "conservative",
            AgentStyle.LONGSHOT: "intuition",
            AgentStyle.DATA: "analyst",
            AgentStyle.PACE: "aggressive",
        }
        for style, expected in mapping.items():
            agent = Agent.create(
                agent_id=AgentId("agt_001"),
                user_id=UserId("usr_001"),
                name=AgentName("テスト"),
                base_style=style,
            )
            assert agent.to_character_type() == expected


class TestAgentName:
    """AgentName値オブジェクトのテスト."""

    def test_有効な名前を作成できる(self):
        name = AgentName("ハヤテ")
        assert name.value == "ハヤテ"

    def test_空文字列はエラー(self):
        with pytest.raises(ValueError):
            AgentName("")

    def test_スペースのみはエラー(self):
        with pytest.raises(ValueError):
            AgentName("   ")

    def test_11文字以上はエラー(self):
        with pytest.raises(ValueError):
            AgentName("あ" * 11)

    def test_10文字は有効(self):
        name = AgentName("あ" * 10)
        assert len(name.value) == 10

    def test_前後の空白はトリムされる(self):
        name = AgentName("  ハヤテ  ")
        assert name.value == "ハヤテ"


class TestAgentPerformance:
    """AgentPerformance値オブジェクトのテスト."""

    def test_空の成績(self):
        perf = AgentPerformance.empty()
        assert perf.total_bets == 0
        assert perf.win_rate == 0.0
        assert perf.roi == 0.0

    def test_的中率計算(self):
        perf = AgentPerformance(total_bets=10, wins=3, total_invested=10000, total_return=12000)
        assert perf.win_rate == pytest.approx(0.3)

    def test_回収率計算(self):
        perf = AgentPerformance(total_bets=10, wins=3, total_invested=10000, total_return=12000)
        assert perf.roi == pytest.approx(1.2)

    def test_収支計算(self):
        perf = AgentPerformance(total_bets=10, wins=3, total_invested=10000, total_return=12000)
        assert perf.profit == 2000

    def test_結果記録(self):
        perf = AgentPerformance.empty()
        new_perf = perf.record_result(invested=1000, returned=0, is_win=False)
        assert new_perf.total_bets == 1
        assert new_perf.wins == 0

        new_perf2 = new_perf.record_result(invested=1000, returned=5000, is_win=True)
        assert new_perf2.total_bets == 2
        assert new_perf2.wins == 1

    def test_winsがtotal_betsを超えるとエラー(self):
        with pytest.raises(ValueError):
            AgentPerformance(total_bets=5, wins=6, total_invested=0, total_return=0)


class TestAgentBettingPreference:
    """エージェントの好み設定テスト."""

    def test_デフォルトの好み設定で作成される(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        assert agent.betting_preference == BettingPreference.default()
        assert agent.custom_instructions is None

    def test_好み設定を更新できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        new_pref = BettingPreference(
            bet_type_preference=BetTypePreference.TRIO_FOCUSED,
        )
        agent.update_preference(new_pref, "三連単の1着固定が好き")

        assert agent.betting_preference.bet_type_preference == BetTypePreference.TRIO_FOCUSED
        assert agent.custom_instructions == "三連単の1着固定が好き"

    def test_custom_instructionsは200文字以内(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        with pytest.raises(ValueError, match="200"):
            agent.update_preference(
                BettingPreference.default(),
                "あ" * 201,
            )

    def test_custom_instructionsがNoneでも更新できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        agent.update_preference(BettingPreference.default(), None)
        assert agent.custom_instructions is None
