"""狙い方列挙型."""
from enum import Enum


class TargetStyle(str, Enum):
    """狙い方."""

    HONMEI = "honmei"
    MEDIUM_LONGSHOT = "medium_longshot"
    BIG_LONGSHOT = "big_longshot"
