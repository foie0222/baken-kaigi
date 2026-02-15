"""DynamoDB エージェントリポジトリ実装."""
import os
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from src.domain.entities import Agent
from src.domain.enums import AgentStyle
from src.domain.identifiers import AgentId, UserId
from src.domain.ports.agent_repository import AgentRepository
from src.domain.value_objects import AgentName, AgentPerformance, BettingPreference


def _floats_to_decimal(d: dict) -> dict:
    """dict 内の float 値を Decimal に変換する（DynamoDB は float を拒否する）."""
    return {k: Decimal(str(v)) if isinstance(v, float) else v for k, v in d.items()}


class DynamoDBAgentRepository(AgentRepository):
    """DynamoDB エージェントリポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._table_name = os.environ.get("AGENT_TABLE_NAME", "baken-kaigi-agent")
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def save(self, agent: Agent) -> None:
        """エージェントを保存する."""
        item = self._to_dynamodb_item(agent)
        self._table.put_item(Item=item)

    def find_by_id(self, agent_id: AgentId) -> Agent | None:
        """エージェントIDで検索する."""
        response = self._table.get_item(Key={"agent_id": str(agent_id.value)})
        item = response.get("Item")
        if item is None:
            return None
        return self._from_dynamodb_item(item)

    def find_by_user_id(self, user_id: UserId) -> Agent | None:
        """ユーザーIDでエージェントを検索する."""
        uid_str = str(user_id.value)
        response = self._table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(uid_str),
        )
        items = response["Items"]
        if not items:
            return None
        return self._from_dynamodb_item(items[0])

    def delete(self, agent_id: AgentId) -> None:
        """エージェントを削除する."""
        self._table.delete_item(Key={"agent_id": str(agent_id.value)})

    @staticmethod
    def _to_dynamodb_item(agent: Agent) -> dict:
        """Agent を DynamoDB アイテムに変換する."""
        item = {
            "agent_id": str(agent.agent_id.value),
            "user_id": str(agent.user_id.value),
            "name": str(agent.name.value),
            "base_style": str(agent.base_style.value),
            "performance": agent.performance.to_dict(),
            "betting_preference": _floats_to_decimal(agent.betting_preference.to_dict()),
            "created_at": agent.created_at.isoformat(),
            "updated_at": agent.updated_at.isoformat(),
        }
        if agent.custom_instructions is not None:
            item["custom_instructions"] = agent.custom_instructions
        return item

    @staticmethod
    def _from_dynamodb_item(item: dict) -> Agent:
        """DynamoDB アイテムから Agent を復元する."""
        perf_data = item["performance"]

        return Agent(
            agent_id=AgentId(item["agent_id"]),
            user_id=UserId(item["user_id"]),
            name=AgentName(item["name"]),
            base_style=AgentStyle(item["base_style"]),
            performance=AgentPerformance(
                total_bets=int(perf_data["total_bets"]),
                wins=int(perf_data["wins"]),
                total_invested=int(perf_data["total_invested"]),
                total_return=int(perf_data["total_return"]),
            ),
            betting_preference=BettingPreference.from_dict(item.get("betting_preference")),
            custom_instructions=item.get("custom_instructions"),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )
