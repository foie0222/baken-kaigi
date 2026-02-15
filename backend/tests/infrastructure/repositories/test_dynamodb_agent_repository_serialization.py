"""DynamoDBリポジトリのシリアライズテスト."""
from src.domain.entities import Agent
from src.domain.enums import AgentStyle, BetTypePreference
from src.domain.identifiers import AgentId, UserId
from src.domain.value_objects import AgentName, BettingPreference
from src.infrastructure.repositories.dynamodb_agent_repository import DynamoDBAgentRepository


class TestDynamoDBAgentSerialization:
    """DynamoDBシリアライズのテスト."""

    def test_好み設定ありのエージェントをシリアライズできる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        agent.update_preference(
            BettingPreference(
                bet_type_preference=BetTypePreference.TRIO_FOCUSED,
            ),
            "三連単が好き",
        )
        item = DynamoDBAgentRepository._to_dynamodb_item(agent)
        assert item["betting_preference"] == {
            "bet_type_preference": "trio_focused",
            "min_probability": 0.01,
            "max_probability": 0.50,
            "min_ev": 1.0,
            "max_ev": 10.0,
        }
        assert item["custom_instructions"] == "三連単が好き"

    def test_好み設定ありのアイテムからエージェントを復元できる(self):
        item = {
            "agent_id": "agt_001",
            "user_id": "usr_001",
            "name": "ハヤテ",
            "base_style": "solid",
            "performance": {
                "total_bets": 0,
                "wins": 0,
                "total_invested": 0,
                "total_return": 0,
            },
            "betting_preference": {
                "bet_type_preference": "trio_focused",
            },
            "custom_instructions": "三連単が好き",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        agent = DynamoDBAgentRepository._from_dynamodb_item(item)
        assert agent.betting_preference.bet_type_preference == BetTypePreference.TRIO_FOCUSED
        assert agent.custom_instructions == "三連単が好き"

    def test_好み設定なしの既存アイテムから復元するとデフォルト(self):
        item = {
            "agent_id": "agt_001",
            "user_id": "usr_001",
            "name": "ハヤテ",
            "base_style": "solid",
            "performance": {
                "total_bets": 0,
                "wins": 0,
                "total_invested": 0,
                "total_return": 0,
            },
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        agent = DynamoDBAgentRepository._from_dynamodb_item(item)
        assert agent.betting_preference == BettingPreference.default()
        assert agent.custom_instructions is None

    def test_旧データにtarget_styleとpriorityが含まれていても復元できる(self):
        item = {
            "agent_id": "agt_001",
            "user_id": "usr_001",
            "name": "ハヤテ",
            "base_style": "solid",
            "performance": {
                "total_bets": 0,
                "wins": 0,
                "total_invested": 0,
                "total_return": 0,
            },
            "betting_preference": {
                "bet_type_preference": "trio_focused",
                "target_style": "big_longshot",
                "priority": "roi",
            },
            "custom_instructions": "三連単が好き",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        agent = DynamoDBAgentRepository._from_dynamodb_item(item)
        assert agent.betting_preference.bet_type_preference == BetTypePreference.TRIO_FOCUSED
        assert agent.custom_instructions == "三連単が好き"
