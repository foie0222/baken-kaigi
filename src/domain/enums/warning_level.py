"""警告レベルの列挙型."""
from enum import Enum


class WarningLevel(Enum):
    """掛け金フィードバックの警告レベル."""

    NONE = "none"  # 警告なし
    CAUTION = "caution"  # 注意（80%接近）
    WARNING = "warning"  # 警告（超過）
