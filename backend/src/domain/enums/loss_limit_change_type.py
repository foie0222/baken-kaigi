"""負け額限度額変更タイプの列挙型."""
from enum import Enum


class LossLimitChangeType(Enum):
    """負け額限度額の変更タイプ."""

    INCREASE = "increase"  # 増額
    DECREASE = "decrease"  # 減額
