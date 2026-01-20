"""カートアイテム識別子の値オブジェクト."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ItemId:
    """カート内アイテムのローカル識別子."""

    value: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value:
            raise ValueError("ItemId cannot be empty")

    @classmethod
    def generate(cls) -> ItemId:
        """新しいItemIdを生成する."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
