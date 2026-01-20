"""レース識別子の値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RaceId:
    """外部システムのレースID（外部参照用）."""

    value: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value:
            raise ValueError("RaceId cannot be empty")

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
