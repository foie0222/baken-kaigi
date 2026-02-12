"""DynamoDB 購入注文リポジトリ実装."""
import os
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key

from src.domain.entities import PurchaseOrder
from src.domain.enums import IpatBetType, IpatVenueCode, PurchaseStatus
from src.domain.identifiers import CartId, PurchaseId, UserId
from src.domain.ports import PurchaseOrderRepository
from src.domain.value_objects import IpatBetLine, Money


class DynamoDBPurchaseOrderRepository(PurchaseOrderRepository):
    """DynamoDB 購入注文リポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._table_name = os.environ.get(
            "PURCHASE_ORDER_TABLE_NAME", "baken-kaigi-purchase-order"
        )
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def save(self, order: PurchaseOrder) -> None:
        """購入注文を保存する."""
        item = self._to_dynamodb_item(order)
        self._table.put_item(Item=item)

    def find_by_id(self, purchase_id: PurchaseId) -> PurchaseOrder | None:
        """購入注文IDで検索する."""
        response = self._table.get_item(Key={"purchase_id": str(purchase_id.value)})
        item = response.get("Item")
        if item is None:
            return None
        return self._from_dynamodb_item(item)

    def find_by_user_id(self, user_id: UserId) -> list[PurchaseOrder]:
        """ユーザーIDで検索する."""
        response = self._table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(str(user_id.value)),
            ScanIndexForward=False,
        )
        items = response.get("Items", [])
        return [self._from_dynamodb_item(item) for item in items]

    @staticmethod
    def _to_dynamodb_item(order: PurchaseOrder) -> dict:
        """PurchaseOrder を DynamoDB アイテムに変換する."""
        item: dict = {
            "purchase_id": str(order.id.value),
            "user_id": str(order.user_id.value),
            "cart_id": str(order.cart_id.value),
            "status": order.status.value,
            "total_amount": order.total_amount.value,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "bet_lines": [
                {
                    "opdt": line.opdt,
                    "venue_code": line.venue_code.value,
                    "race_number": line.race_number,
                    "bet_type": line.bet_type.value,
                    "number": line.number,
                    "amount": line.amount,
                }
                for line in order.bet_lines
            ],
        }
        if order.error_message is not None:
            item["error_message"] = order.error_message
        return item

    @staticmethod
    def _from_dynamodb_item(item: dict) -> PurchaseOrder:
        """DynamoDB アイテムから PurchaseOrder を復元する."""
        bet_lines = [
            IpatBetLine(
                opdt=line["opdt"],
                venue_code=IpatVenueCode(line["venue_code"]),
                race_number=int(line["race_number"]),
                bet_type=IpatBetType(line["bet_type"]),
                number=line["number"],
                amount=int(line["amount"]),
            )
            for line in item.get("bet_lines", [])
        ]

        return PurchaseOrder(
            id=PurchaseId(item["purchase_id"]),
            user_id=UserId(item["user_id"]),
            cart_id=CartId(item["cart_id"]),
            bet_lines=bet_lines,
            status=PurchaseStatus(item["status"]),
            total_amount=Money.of(int(item["total_amount"])),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            error_message=item.get("error_message"),
        )
