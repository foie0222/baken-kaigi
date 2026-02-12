"""DynamoDB エージェント振り返りリポジトリ実装."""
import json
import os
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key

from src.domain.entities import AgentReview, BetResult
from src.domain.identifiers import AgentId, RaceId, ReviewId
from src.domain.ports.agent_review_repository import AgentReviewRepository


class DynamoDBAgentReviewRepository(AgentReviewRepository):
    """DynamoDB エージェント振り返りリポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._table_name = os.environ.get("AGENT_REVIEW_TABLE_NAME", "baken-kaigi-agent-review")
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def save(self, review: AgentReview) -> None:
        """振り返りを保存する."""
        item = self._to_dynamodb_item(review)
        self._table.put_item(Item=item)

    def find_by_id(self, review_id: ReviewId) -> AgentReview | None:
        """振り返りIDで検索する."""
        response = self._table.get_item(Key={"review_id": str(review_id.value)})
        item = response.get("Item")
        if item is None:
            return None
        return self._from_dynamodb_item(item)

    def find_by_agent_id(self, agent_id: AgentId, limit: int = 20) -> list[AgentReview]:
        """エージェントIDで振り返り一覧を取得する（新しい順）."""
        response = self._table.query(
            IndexName="agent_id-index",
            KeyConditionExpression=Key("agent_id").eq(str(agent_id.value)),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = response.get("Items", [])
        return [self._from_dynamodb_item(item) for item in items]

    @staticmethod
    def _to_dynamodb_item(review: AgentReview) -> dict:
        """AgentReview を DynamoDB アイテムに変換する."""
        return {
            "review_id": str(review.review_id.value),
            "agent_id": str(review.agent_id.value),
            "race_id": str(review.race_id.value),
            "race_date": review.race_date,
            "race_name": review.race_name,
            "bet_results": json.dumps(
                [
                    {
                        "bet_type": r.bet_type,
                        "horse_numbers": r.horse_numbers,
                        "amount": r.amount,
                        "result": r.result,
                        "payout": r.payout,
                    }
                    for r in review.bet_results
                ],
                ensure_ascii=False,
            ),
            "total_invested": review.total_invested,
            "total_return": review.total_return,
            "review_text": review.review_text,
            "learnings": review.learnings,
            "stats_change": review.stats_change,
            "created_at": review.created_at.isoformat(),
        }

    @staticmethod
    def _from_dynamodb_item(item: dict) -> AgentReview:
        """DynamoDB アイテムから AgentReview を復元する."""
        bet_results_raw = item.get("bet_results", "[]")
        if isinstance(bet_results_raw, str):
            bet_results_data = json.loads(bet_results_raw)
        else:
            bet_results_data = bet_results_raw

        bet_results = [
            BetResult(
                bet_type=r["bet_type"],
                horse_numbers=r["horse_numbers"],
                amount=int(r["amount"]),
                result=r["result"],
                payout=int(r["payout"]),
            )
            for r in bet_results_data
        ]

        stats_change = item.get("stats_change", {})
        stats_change = {k: int(v) for k, v in stats_change.items()}

        return AgentReview(
            review_id=ReviewId(item["review_id"]),
            agent_id=AgentId(item["agent_id"]),
            race_id=RaceId(item["race_id"]),
            race_date=item["race_date"],
            race_name=item["race_name"],
            bet_results=bet_results,
            total_invested=int(item["total_invested"]),
            total_return=int(item["total_return"]),
            review_text=item["review_text"],
            learnings=item.get("learnings", []),
            stats_change=stats_change,
            created_at=datetime.fromisoformat(item["created_at"]),
        )
