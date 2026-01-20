"""相談セッション集約ルート."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..enums import SessionStatus
from ..identifiers import SessionId, UserId
from ..value_objects import AmountFeedback, DataFeedback, Money

from .cart_item import CartItem
from .message import Message


@dataclass
class ConsultationSession:
    """AIとの相談セッション（集約ルート）."""

    session_id: SessionId
    user_id: UserId | None = None
    _cart_snapshot: list[CartItem] = field(default_factory=list)
    _messages: list[Message] = field(default_factory=list)
    _data_feedbacks: list[DataFeedback] = field(default_factory=list)
    _amount_feedback: AmountFeedback | None = None
    status: SessionStatus = SessionStatus.NOT_STARTED
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None

    @classmethod
    def create(cls, user_id: UserId | None = None) -> ConsultationSession:
        """新しいセッションを作成する."""
        return cls(
            session_id=SessionId.generate(),
            user_id=user_id,
            _cart_snapshot=[],
            _messages=[],
            _data_feedbacks=[],
            _amount_feedback=None,
            status=SessionStatus.NOT_STARTED,
            started_at=datetime.now(),
            ended_at=None,
        )

    def start(self, cart_items: list[CartItem]) -> None:
        """セッションを開始する."""
        if self.status != SessionStatus.NOT_STARTED:
            raise ValueError("Session can only be started from NOT_STARTED status")
        if not cart_items:
            raise ValueError("Cannot start session with empty cart")

        self._cart_snapshot = list(cart_items)
        self.status = SessionStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def add_user_message(self, content: str) -> Message:
        """ユーザーメッセージを追加する."""
        self._ensure_in_progress()
        message = Message.create_user_message(content)
        self._messages.append(message)
        return message

    def add_ai_message(self, content: str) -> Message:
        """AIメッセージを追加する."""
        self._ensure_in_progress()
        message = Message.create_ai_message(content)
        self._messages.append(message)
        return message

    def add_system_message(self, content: str) -> Message:
        """システムメッセージを追加する."""
        self._ensure_in_progress()
        message = Message.create_system_message(content)
        self._messages.append(message)
        return message

    def set_data_feedbacks(self, feedbacks: list[DataFeedback]) -> None:
        """データフィードバックを設定する."""
        self._ensure_in_progress()
        self._data_feedbacks = list(feedbacks)

    def set_amount_feedback(self, feedback: AmountFeedback) -> None:
        """掛け金フィードバックを設定する."""
        self._ensure_in_progress()
        self._amount_feedback = feedback

    def end(self) -> None:
        """セッションを終了する."""
        self._ensure_in_progress()
        self.status = SessionStatus.COMPLETED
        self.ended_at = datetime.now()

    def get_total_amount(self) -> Money:
        """合計掛け金を取得する."""
        total = Money.zero()
        for item in self._cart_snapshot:
            total = total.add(item.get_amount())
        return total

    def is_limit_exceeded(self, remaining_limit: Money) -> bool:
        """限度額超過判定."""
        return self.get_total_amount().is_greater_than(remaining_limit)

    def get_cart_snapshot(self) -> list[CartItem]:
        """相談対象の買い目を取得（防御的コピー）."""
        return list(self._cart_snapshot)

    def get_messages(self) -> list[Message]:
        """会話履歴を取得（防御的コピー）."""
        return list(self._messages)

    def get_data_feedbacks(self) -> list[DataFeedback]:
        """データフィードバックを取得（防御的コピー）."""
        return list(self._data_feedbacks)

    def get_amount_feedback(self) -> AmountFeedback | None:
        """掛け金フィードバックを取得."""
        return self._amount_feedback

    def _ensure_in_progress(self) -> None:
        """IN_PROGRESS状態であることを確認する."""
        if self.status != SessionStatus.IN_PROGRESS:
            raise ValueError("Operation requires session to be IN_PROGRESS")
