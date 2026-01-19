"""メッセージエンティティ."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..enums import MessageType
from ..identifiers import MessageId


@dataclass(frozen=True)
class Message:
    """相談セッション内の個々の発言（ConsultationSession集約内でのみ意味を持つ）."""

    message_id: MessageId
    type: MessageType
    content: str
    timestamp: datetime

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.content:
            raise ValueError("Message content cannot be empty")

    @classmethod
    def create_user_message(
        cls, content: str, timestamp: datetime | None = None
    ) -> Message:
        """ユーザーメッセージを作成する."""
        return cls(
            message_id=MessageId.generate(),
            type=MessageType.USER,
            content=content,
            timestamp=timestamp or datetime.now(),
        )

    @classmethod
    def create_ai_message(
        cls, content: str, timestamp: datetime | None = None
    ) -> Message:
        """AIメッセージを作成する."""
        return cls(
            message_id=MessageId.generate(),
            type=MessageType.AI,
            content=content,
            timestamp=timestamp or datetime.now(),
        )

    @classmethod
    def create_system_message(
        cls, content: str, timestamp: datetime | None = None
    ) -> Message:
        """システムメッセージを作成する."""
        return cls(
            message_id=MessageId.generate(),
            type=MessageType.SYSTEM,
            content=content,
            timestamp=timestamp or datetime.now(),
        )

    def is_from_user(self) -> bool:
        """ユーザーからのメッセージか判定."""
        return self.type == MessageType.USER

    def is_from_ai(self) -> bool:
        """AIからのメッセージか判定."""
        return self.type == MessageType.AI

    def is_system(self) -> bool:
        """システムメッセージか判定."""
        return self.type == MessageType.SYSTEM
