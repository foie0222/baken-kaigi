"""メッセージ識別子の値オブジェクト."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class MessageId:
    """セッション内メッセージのローカル識別子."""

    value: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value:
            raise ValueError("MessageId cannot be empty")

    @classmethod
    def generate(cls) -> MessageId:
        """新しいMessageIdを生成する."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
