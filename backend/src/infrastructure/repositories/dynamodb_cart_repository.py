"""カートリポジトリのDynamoDB実装."""
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from src.domain.entities import Cart
from src.domain.entities.cart_item import CartItem
from src.domain.enums import BetType
from src.domain.identifiers import CartId, ItemId, RaceId, UserId
from src.domain.ports import CartRepository
from src.domain.value_objects import BetSelection, HorseNumbers, Money

# TTL: 24時間
TTL_HOURS = 24


class DynamoDBCartRepository(CartRepository):
    """カートリポジトリのDynamoDB実装."""

    def __init__(self, table_name: str | None = None) -> None:
        """初期化."""
        self._table_name = table_name or os.environ.get(
            "CART_TABLE_NAME", "baken-kaigi-cart"
        )
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def save(self, cart: Cart) -> None:
        """カートを保存する."""
        item = self._to_dynamodb_item(cart)
        self._table.put_item(Item=item)

    def find_by_id(self, cart_id: CartId) -> Cart | None:
        """カートIDで検索する."""
        response = self._table.get_item(Key={"cart_id": str(cart_id.value)})
        item = response.get("Item")
        if item is None:
            return None
        return self._from_dynamodb_item(item)

    def find_by_user_id(self, user_id: UserId) -> Cart | None:
        """ユーザーIDで検索する（GSI使用）."""
        response = self._table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(str(user_id.value)),
            Limit=1,
        )
        items = response["Items"]
        if not items:
            return None
        return self._from_dynamodb_item(items[0])

    def delete(self, cart_id: CartId) -> None:
        """カートを削除する."""
        self._table.delete_item(Key={"cart_id": str(cart_id.value)})

    def _to_dynamodb_item(self, cart: Cart) -> dict[str, Any]:
        """CartエンティティをDynamoDBアイテムに変換."""
        ttl = int((datetime.now(timezone.utc) + timedelta(hours=TTL_HOURS)).timestamp())

        items = []
        for item in cart.get_items():
            items.append(
                {
                    "item_id": str(item.item_id.value),
                    "race_id": str(item.race_id.value),
                    "race_name": item.race_name,
                    "bet_type": item.bet_selection.bet_type.value,
                    "horse_numbers": item.bet_selection.horse_numbers.to_list(),
                    "amount": item.bet_selection.amount.value,
                    "added_at": item.added_at.isoformat(),
                }
            )

        return {
            "cart_id": str(cart.cart_id.value),
            "user_id": str(cart.user_id.value) if cart.user_id else "__anonymous__",
            "items": items,
            "created_at": cart.created_at.isoformat(),
            "updated_at": cart.updated_at.isoformat(),
            "ttl": ttl,
        }

    def _from_dynamodb_item(self, item: dict[str, Any]) -> Cart:
        """DynamoDBアイテムをCartエンティティに変換."""
        cart_id = CartId(item["cart_id"])
        user_id_str = item.get("user_id")
        user_id = None if user_id_str == "__anonymous__" else UserId(user_id_str)

        cart_items = []
        for item_data in item.get("items", []):
            # Decimal を int に変換
            horse_numbers = [self._to_int(n) for n in item_data["horse_numbers"]]
            amount = self._to_int(item_data["amount"])

            bet_selection = BetSelection(
                bet_type=BetType(item_data["bet_type"]),
                horse_numbers=HorseNumbers.from_list(horse_numbers),
                amount=Money(amount),
            )
            cart_item = CartItem(
                item_id=ItemId(item_data["item_id"]),
                race_id=RaceId(item_data["race_id"]),
                race_name=item_data["race_name"],
                bet_selection=bet_selection,
                added_at=datetime.fromisoformat(item_data["added_at"]),
            )
            cart_items.append(cart_item)

        return Cart(
            cart_id=cart_id,
            user_id=user_id,
            _items=cart_items,
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )

    @staticmethod
    def _to_int(value: Any) -> int:
        """Decimalをintに変換."""
        if isinstance(value, Decimal):
            return int(value)
        return int(value)
