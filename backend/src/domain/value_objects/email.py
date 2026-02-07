"""メールアドレスを表現する値オブジェクト."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    """メールアドレスの値オブジェクト."""

    value: str

    # RFC 5322 に基づく簡易的なメールアドレスパターン
    _PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value:
            raise ValueError("Email cannot be empty")
        if not self._PATTERN.match(self.value):
            raise ValueError(f"Invalid email format: {self.value}")

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
