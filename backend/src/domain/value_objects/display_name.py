"""表示名を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayName:
    """表示名の値オブジェクト."""

    value: str

    _MIN_LENGTH = 1
    _MAX_LENGTH = 50

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value or not self.value.strip():
            raise ValueError("DisplayName cannot be empty")
        if len(self.value) < self._MIN_LENGTH:
            raise ValueError(f"DisplayName must be at least {self._MIN_LENGTH} characters")
        if len(self.value) > self._MAX_LENGTH:
            raise ValueError(f"DisplayName must be at most {self._MAX_LENGTH} characters")

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
