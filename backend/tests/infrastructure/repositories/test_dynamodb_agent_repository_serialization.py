"""DynamoDBリポジトリのシリアライズテスト."""
from src.domain.entities import Agent
from src.domain.enums import AgentStyle, BetTypePreference, TargetStyle, BettingPriority
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
                target_style=TargetStyle.BIG_LONGSHOT,
                priority=BettingPriority.ROI,
            ),
            "三連単が好き",
        )
        item = DynamoDBAgentRepository._to_dynamodb_item(agent)
        assert item["betting_preference"] == {
            "bet_type_preference": "trio_focused",
            "target_style": "big_longshot",
            "priority": "roi",
        }
        assert item["custom_instructions"] == "三連単が好き"

    def test_好み設定ありのアイテムからエージェントを復元できる(self):
        item = {
            "agent_id": "agt_001",
            "user_id": "usr_001",
            "name": "ハヤテ",
            "base_style": "solid",
            "performance": {},
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

    def test_好み設定なしの既存アイテムから復元するとデフォルト(self):
        item = {
            "agent_id": "agt_001",
            "user_id": "usr_001",
            "name": "ハヤテ",
            "base_style": "solid",
            "performance": {},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        agent = DynamoDBAgentRepository._from_dynamodb_item(item)
        assert agent.betting_preference == BettingPreference.default()
        assert agent.custom_instructions is None
