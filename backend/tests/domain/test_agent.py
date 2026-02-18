"""エージェントエンティティのテスト."""
import pytest

from src.domain.entities import Agent
from src.domain.enums import BetTypePreference
from src.domain.identifiers import AgentId, UserId
from src.domain.value_objects import AgentName, BettingPreference


class TestAgent:
    """Agentエンティティのテスト."""

    def test_エージェントを作成できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
        )
        assert agent.name.value == "ハヤテ"
        assert agent.betting_preference == BettingPreference.default()
        assert agent.custom_instructions is None


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


class TestAgentBettingPreference:
    """エージェントの好み設定テスト."""

    def test_デフォルトの好み設定で作成される(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
        )
        assert agent.betting_preference == BettingPreference.default()
        assert agent.custom_instructions is None

    def test_好み設定を更新できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
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
        )
        agent.update_preference(BettingPreference.default(), None)
        assert agent.custom_instructions is None

    def test_to_dictにrace_budgetが含まれる(self):
        pref = BettingPreference(
            bet_type_preference=BetTypePreference.AUTO,
            race_budget=5000,
        )
        d = pref.to_dict()
        assert d["race_budget"] == 5000

    def test_from_dictでrace_budgetが復元される(self):
        data = {
            "bet_type_preference": "auto",
            "race_budget": 3000,
        }
        pref = BettingPreference.from_dict(data)
        assert pref.race_budget == 3000

    def test_from_dictでrace_budget省略時はデフォルト0(self):
        data = {"bet_type_preference": "auto"}
        pref = BettingPreference.from_dict(data)
        assert pref.race_budget == 0
