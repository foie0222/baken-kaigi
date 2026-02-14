"""券種好み列挙型."""
from enum import Enum


class BetTypePreference(str, Enum):
    """券種の好み."""

    TRIO_FOCUSED = "trio_focused"
    EXACTA_FOCUSED = "exacta_focused"
    QUINELLA_FOCUSED = "quinella_focused"
    WIDE_FOCUSED = "wide_focused"
    AUTO = "auto"
