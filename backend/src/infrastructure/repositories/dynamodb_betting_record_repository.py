"""DynamoDB 投票記録リポジトリ実装."""
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

from src.domain.entities import BettingRecord
from src.domain.enums import BetType, BettingRecordStatus
from src.domain.identifiers import BettingRecordId, RaceId, UserId
from src.domain.ports import BettingRecordRepository
from src.domain.value_objects import HorseNumbers, Money


class DynamoDBBettingRecordRepository(BettingRecordRepository):
    """DynamoDB 投票記録リポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._table_name = os.environ.get(
            "BETTING_RECORD_TABLE_NAME", "baken-kaigi-betting-record"
        )
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def save(self, record: BettingRecord) -> None:
        """投票記録を保存する."""
        item = self._to_dynamodb_item(record)
        self._table.put_item(Item=item)

    def find_by_id(self, record_id: BettingRecordId) -> BettingRecord | None:
        """投票記録IDで検索する."""
        response = self._table.get_item(Key={"record_id": record_id.value})
        item = response.get("Item")
        if item is None:
            return None
        return self._from_dynamodb_item(item)

    def find_by_user_id(
        self,
        user_id: UserId,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        venue: Optional[str] = None,
        bet_type: Optional[BetType] = None,
    ) -> list[BettingRecord]:
        """ユーザーIDで検索する（GSI使用、フィルタ付き）."""
        key_condition = Key("user_id").eq(user_id.value)
        if from_date is not None and to_date is not None:
            key_condition = key_condition & Key("race_date").between(
                from_date.isoformat(), to_date.isoformat()
            )
        elif from_date is not None:
            key_condition = key_condition & Key("race_date").gte(from_date.isoformat())
        elif to_date is not None:
            key_condition = key_condition & Key("race_date").lte(to_date.isoformat())

        filter_expression = None
        if venue is not None:
            filter_expression = Attr("venue").eq(venue)
        if bet_type is not None:
            bet_filter = Attr("bet_type").eq(bet_type.value)
            filter_expression = (
                filter_expression & bet_filter
                if filter_expression is not None
                else bet_filter
            )

        query_kwargs = {
            "IndexName": "user_id-race_date-index",
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": False,
        }
        if filter_expression is not None:
            query_kwargs["FilterExpression"] = filter_expression

        response = self._table.query(**query_kwargs)
        items = response.get("Items", [])
        return [self._from_dynamodb_item(item) for item in items]

    @staticmethod
    def _to_dynamodb_item(record: BettingRecord) -> dict:
        """BettingRecord を DynamoDB アイテムに変換する."""
        item: dict = {
            "record_id": record.record_id.value,
            "user_id": record.user_id.value,
            "race_id": record.race_id.value,
            "race_name": record.race_name,
            "race_date": record.race_date.isoformat(),
            "venue": record.venue,
            "bet_type": record.bet_type.value,
            "horse_numbers": [Decimal(str(n)) for n in record.horse_numbers.to_list()],
            "amount": Decimal(str(record.amount.value)),
            "payout": Decimal(str(record.payout.value)),
            "profit": Decimal(str(record.profit.value)),
            "status": record.status.value,
            "created_at": record.created_at.isoformat(),
        }
        if record.settled_at is not None:
            item["settled_at"] = record.settled_at.isoformat()
        return item

    @staticmethod
    def _from_dynamodb_item(item: dict) -> BettingRecord:
        """DynamoDB アイテムから BettingRecord を復元する."""
        settled_at = None
        if "settled_at" in item:
            settled_at = datetime.fromisoformat(item["settled_at"])

        return BettingRecord(
            record_id=BettingRecordId(item["record_id"]),
            user_id=UserId(item["user_id"]),
            race_id=RaceId(item["race_id"]),
            race_name=item["race_name"],
            race_date=date.fromisoformat(item["race_date"]),
            venue=item["venue"],
            bet_type=BetType(item["bet_type"]),
            horse_numbers=HorseNumbers.from_list(
                [int(n) for n in item["horse_numbers"]]
            ),
            amount=Money.of(int(item["amount"])),
            payout=Money.of(int(item["payout"])),
            profit=Money.of(int(item["profit"])),
            status=BettingRecordStatus(item["status"]),
            created_at=datetime.fromisoformat(item["created_at"]),
            settled_at=settled_at,
        )
