"""エージェント識別子の値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentId:
    """エージェントのID."""

    value: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value:
            raise ValueError("AgentId cannot be empty")

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
