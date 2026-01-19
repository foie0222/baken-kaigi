"""カート識別子の値オブジェクト."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CartId:
    """カートの一意識別子（UUID形式）."""

    value: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value:
            raise ValueError("CartId cannot be empty")

    @classmethod
    def generate(cls) -> CartId:
        """新しいCartIdを生成する."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
