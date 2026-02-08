"""DynamoDB 負け額限度額変更リポジトリ実装."""
import os
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Attr, Key

from src.domain.entities import LossLimitChange
from src.domain.enums import LossLimitChangeStatus, LossLimitChangeType
from src.domain.identifiers import LossLimitChangeId, UserId
from src.domain.ports.loss_limit_change_repository import LossLimitChangeRepository
from src.domain.value_objects import Money


class DynamoDBLossLimitChangeRepository(LossLimitChangeRepository):
    """DynamoDB 負け額限度額変更リポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._table_name = os.environ.get(
            "LOSS_LIMIT_CHANGE_TABLE_NAME", "baken-kaigi-loss-limit-change"
        )
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def save(self, change: LossLimitChange) -> None:
        """変更リクエストを保存する."""
        item = self._to_dynamodb_item(change)
        self._table.put_item(Item=item)

    def find_by_id(self, change_id: LossLimitChangeId) -> LossLimitChange | None:
        """変更リクエストIDで検索する."""
        response = self._table.get_item(Key={"change_id": change_id.value})
        item = response.get("Item")
        if item is None:
            return None
        return self._from_dynamodb_item(item)

    def find_pending_by_user_id(self, user_id: UserId) -> list[LossLimitChange]:
        """ユーザーIDで保留中の変更リクエストを検索する."""
        response = self._table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(user_id.value),
            FilterExpression=Attr("status").eq(LossLimitChangeStatus.PENDING.value),
        )
        items = response.get("Items", [])
        return [self._from_dynamodb_item(item) for item in items]

    def find_by_user_id(self, user_id: UserId) -> list[LossLimitChange]:
        """ユーザーIDで変更リクエストを検索する."""
        response = self._table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(user_id.value),
        )
        items = response.get("Items", [])
        return [self._from_dynamodb_item(item) for item in items]

    @staticmethod
    def _to_dynamodb_item(change: LossLimitChange) -> dict:
        """LossLimitChange を DynamoDB アイテムに変換する."""
        return {
            "change_id": change.change_id.value,
            "user_id": change.user_id.value,
            "current_limit": change.current_limit.value,
            "requested_limit": change.requested_limit.value,
            "change_type": change.change_type.value,
            "status": change.status.value,
            "effective_at": change.effective_at.isoformat(),
            "requested_at": change.requested_at.isoformat(),
        }

    @staticmethod
    def _from_dynamodb_item(item: dict) -> LossLimitChange:
        """DynamoDB アイテムから LossLimitChange を復元する."""
        return LossLimitChange(
            change_id=LossLimitChangeId(item["change_id"]),
            user_id=UserId(item["user_id"]),
            current_limit=Money.of(int(item["current_limit"])),
            requested_limit=Money.of(int(item["requested_limit"])),
            change_type=LossLimitChangeType(item["change_type"]),
            status=LossLimitChangeStatus(item["status"]),
            effective_at=datetime.fromisoformat(item["effective_at"]),
            requested_at=datetime.fromisoformat(item["requested_at"]),
        )
