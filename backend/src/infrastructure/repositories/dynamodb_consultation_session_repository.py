"""相談セッションリポジトリのDynamoDB実装."""
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from src.domain.entities import ConsultationSession
from src.domain.entities.cart_item import CartItem
from src.domain.entities.message import Message
from src.domain.enums import BetType, MessageType, SessionStatus, WarningLevel
from src.domain.identifiers import ItemId, MessageId, RaceId, SessionId, UserId
from src.domain.ports import ConsultationSessionRepository
from src.domain.value_objects import (
    AmountFeedback,
    BetSelection,
    DataFeedback,
    HorseDataSummary,
    HorseNumbers,
    Money,
)

# TTL: 24時間
TTL_HOURS = 24


class DynamoDBConsultationSessionRepository(ConsultationSessionRepository):
    """相談セッションリポジトリのDynamoDB実装."""

    def __init__(self, table_name: str | None = None) -> None:
        """初期化."""
        self._table_name = table_name or os.environ.get(
            "SESSION_TABLE_NAME", "baken-kaigi-consultation-session"
        )
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def save(self, session: ConsultationSession) -> None:
        """セッションを保存する."""
        item = self._to_dynamodb_item(session)
        # DynamoDBはfloat非対応のため、Decimalに変換
        item = self._convert_floats_to_decimal(item)
        self._table.put_item(Item=item)

    def find_by_id(self, session_id: SessionId) -> ConsultationSession | None:
        """セッションIDで検索する."""
        response = self._table.get_item(Key={"session_id": session_id.value})
        item = response.get("Item")
        if item is None:
            return None
        return self._from_dynamodb_item(item)

    def find_by_user_id(self, user_id: UserId) -> list[ConsultationSession]:
        """ユーザーIDで検索する（GSI使用）."""
        response = self._table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(user_id.value),
        )
        items = response.get("Items", [])
        return [self._from_dynamodb_item(item) for item in items]

    def delete(self, session_id: SessionId) -> None:
        """セッションを削除する."""
        self._table.delete_item(Key={"session_id": session_id.value})

    def _to_dynamodb_item(self, session: ConsultationSession) -> dict[str, Any]:
        """ConsultationSessionエンティティをDynamoDBアイテムに変換."""
        ttl = int((datetime.now() + timedelta(hours=TTL_HOURS)).timestamp())

        # カートスナップショットの変換
        cart_snapshot = []
        for item in session.get_cart_snapshot():
            cart_snapshot.append(self._cart_item_to_dict(item))

        # メッセージの変換
        messages = []
        for msg in session.get_messages():
            messages.append(
                {
                    "message_id": msg.message_id.value,
                    "type": msg.type.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                }
            )

        # データフィードバックの変換
        data_feedbacks = []
        for fb in session.get_data_feedbacks():
            horse_summaries = []
            for hs in fb.horse_summaries:
                horse_summaries.append(
                    {
                        "horse_number": hs.horse_number,
                        "horse_name": hs.horse_name,
                        "recent_results": hs.recent_results,
                        "jockey_stats": hs.jockey_stats,
                        "track_suitability": hs.track_suitability,
                        "current_odds": hs.current_odds,
                        "popularity": hs.popularity,
                    }
                )
            data_feedbacks.append(
                {
                    "cart_item_id": fb.cart_item_id.value,
                    "horse_summaries": horse_summaries,
                    "overall_comment": fb.overall_comment,
                    "generated_at": fb.generated_at.isoformat(),
                }
            )

        # 金額フィードバックの変換
        amount_feedback = None
        af = session.get_amount_feedback()
        if af:
            amount_feedback = {
                "total_amount": af.total_amount.value,
                "remaining_loss_limit": (
                    af.remaining_loss_limit.value if af.remaining_loss_limit else None
                ),
                "average_amount": af.average_amount.value if af.average_amount else None,
                "is_limit_exceeded": af.is_limit_exceeded,
                "warning_level": af.warning_level.value,
                "comment": af.comment,
                "generated_at": af.generated_at.isoformat(),
            }

        return {
            "session_id": session.session_id.value,
            "user_id": session.user_id.value if session.user_id else "__anonymous__",
            "cart_snapshot": cart_snapshot,
            "messages": messages,
            "data_feedbacks": data_feedbacks,
            "amount_feedback": amount_feedback,
            "status": session.status.value,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "ttl": ttl,
        }

    def _from_dynamodb_item(self, item: dict[str, Any]) -> ConsultationSession:
        """DynamoDBアイテムをConsultationSessionエンティティに変換."""
        session_id = SessionId(item["session_id"])
        user_id_str = item.get("user_id")
        user_id = None if user_id_str == "__anonymous__" else UserId(user_id_str)

        # カートスナップショットの復元
        cart_snapshot = []
        for item_data in item.get("cart_snapshot", []):
            cart_snapshot.append(self._dict_to_cart_item(item_data))

        # メッセージの復元
        messages = []
        for msg_data in item.get("messages", []):
            messages.append(
                Message(
                    message_id=MessageId(msg_data["message_id"]),
                    type=MessageType(msg_data["type"]),
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                )
            )

        # データフィードバックの復元
        data_feedbacks = []
        for fb_data in item.get("data_feedbacks", []):
            horse_summaries = []
            for hs_data in fb_data.get("horse_summaries", []):
                horse_summaries.append(
                    HorseDataSummary(
                        horse_number=self._to_int(hs_data["horse_number"]),
                        horse_name=hs_data["horse_name"],
                        recent_results=hs_data["recent_results"],
                        jockey_stats=hs_data["jockey_stats"],
                        track_suitability=hs_data["track_suitability"],
                        current_odds=hs_data["current_odds"],
                        popularity=self._to_int(hs_data["popularity"]),
                    )
                )
            data_feedbacks.append(
                DataFeedback(
                    cart_item_id=ItemId(fb_data["cart_item_id"]),
                    horse_summaries=tuple(horse_summaries),
                    overall_comment=fb_data["overall_comment"],
                    generated_at=datetime.fromisoformat(fb_data["generated_at"]),
                )
            )

        # 金額フィードバックの復元
        amount_feedback = None
        af_data = item.get("amount_feedback")
        if af_data:
            amount_feedback = AmountFeedback(
                total_amount=Money.of(self._to_int(af_data["total_amount"])),
                remaining_loss_limit=(
                    Money.of(self._to_int(af_data["remaining_loss_limit"]))
                    if af_data.get("remaining_loss_limit") is not None
                    else None
                ),
                average_amount=(
                    Money.of(self._to_int(af_data["average_amount"]))
                    if af_data.get("average_amount") is not None
                    else None
                ),
                is_limit_exceeded=af_data["is_limit_exceeded"],
                warning_level=WarningLevel(af_data["warning_level"]),
                comment=af_data["comment"],
                generated_at=datetime.fromisoformat(af_data["generated_at"]),
            )

        ended_at = (
            datetime.fromisoformat(item["ended_at"]) if item.get("ended_at") else None
        )

        return ConsultationSession(
            session_id=session_id,
            user_id=user_id,
            _cart_snapshot=cart_snapshot,
            _messages=messages,
            _data_feedbacks=data_feedbacks,
            _amount_feedback=amount_feedback,
            status=SessionStatus(item["status"]),
            started_at=datetime.fromisoformat(item["started_at"]),
            ended_at=ended_at,
        )

    def _cart_item_to_dict(self, item: CartItem) -> dict[str, Any]:
        """CartItemを辞書に変換."""
        return {
            "item_id": item.item_id.value,
            "race_id": item.race_id.value,
            "race_name": item.race_name,
            "bet_type": item.bet_selection.bet_type.value,
            "horse_numbers": item.bet_selection.horse_numbers.to_list(),
            "amount": item.bet_selection.amount.value,
            "added_at": item.added_at.isoformat(),
        }

    def _dict_to_cart_item(self, data: dict[str, Any]) -> CartItem:
        """辞書からCartItemを復元."""
        horse_numbers = [self._to_int(n) for n in data["horse_numbers"]]
        amount = self._to_int(data["amount"])

        bet_selection = BetSelection(
            bet_type=BetType(data["bet_type"]),
            horse_numbers=HorseNumbers.from_list(horse_numbers),
            amount=Money(amount),
        )
        return CartItem(
            item_id=ItemId(data["item_id"]),
            race_id=RaceId(data["race_id"]),
            race_name=data["race_name"],
            bet_selection=bet_selection,
            added_at=datetime.fromisoformat(data["added_at"]),
        )

    @staticmethod
    def _to_int(value: Any) -> int:
        """Decimalをintに変換."""
        if isinstance(value, Decimal):
            return int(value)
        return value

    @classmethod
    def _convert_floats_to_decimal(cls, obj: Any) -> Any:
        """再帰的にfloatをDecimalに変換（DynamoDB用）."""
        if isinstance(obj, float):
            return Decimal(str(obj))
        if isinstance(obj, dict):
            return {k: cls._convert_floats_to_decimal(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [cls._convert_floats_to_decimal(item) for item in obj]
        return obj
