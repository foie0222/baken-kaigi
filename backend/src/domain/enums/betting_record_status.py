"""投票記録ステータスの列挙型."""
from enum import Enum


class BettingRecordStatus(Enum):
    """投票記録のステータス."""

    PENDING = "pending"
    SETTLED = "settled"
    CANCELLED = "cancelled"

    def get_display_name(self) -> str:
        """日本語表示名を返す."""
        names = {
            BettingRecordStatus.PENDING: "未確定",
            BettingRecordStatus.SETTLED: "確定済",
            BettingRecordStatus.CANCELLED: "取消",
        }
        return names[self]
