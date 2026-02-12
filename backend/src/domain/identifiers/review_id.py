"""振り返り識別子の値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewId:
    """振り返りのID."""

    value: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value:
            raise ValueError("ReviewId cannot be empty")

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
