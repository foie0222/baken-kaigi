"""エージェント名の値オブジェクト."""
from __future__ import annotations

import re
from dataclasses import dataclass

_EMOJI_PATTERN = re.compile(
    "[\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f6ff"
    "\U0001f1e0-\U0001f1ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\U00002702-\U000027b0"
    "\U0000fe0f"
    "\U0000200d]+",
    flags=re.UNICODE,
)

MIN_LENGTH = 1
MAX_LENGTH = 10


@dataclass(frozen=True)
class AgentName:
    """エージェント名（1〜10文字、絵文字不可）."""

    value: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.value or not self.value.strip():
            raise ValueError("AgentName cannot be empty")
        stripped = self.value.strip()
        if len(stripped) < MIN_LENGTH or len(stripped) > MAX_LENGTH:
            raise ValueError(
                f"AgentName must be between {MIN_LENGTH} and {MAX_LENGTH} characters, "
                f"got {len(stripped)}"
            )
        if _EMOJI_PATTERN.search(stripped):
            raise ValueError("AgentName cannot contain emojis")
        # frozen なので object.__setattr__ で設定
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        """文字列表現."""
        return self.value
