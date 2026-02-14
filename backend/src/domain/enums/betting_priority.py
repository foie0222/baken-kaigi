"""重視ポイント列挙型."""
from enum import Enum


class BettingPriority(str, Enum):
    """重視ポイント."""

    HIT_RATE = "hit_rate"
    ROI = "roi"
    BALANCED = "balanced"
