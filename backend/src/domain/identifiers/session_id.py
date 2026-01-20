"""セッション識別子の値オブジェクト."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class SessionId:
    """相談セッションの一意識別子（UUID形式）."""

    value: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value:
            raise ValueError("SessionId cannot be empty")

    @classmethod
    def generate(cls) -> SessionId:
        """新しいSessionIdを生成する."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
