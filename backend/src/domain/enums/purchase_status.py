"""購入ステータスの列挙型."""
from enum import Enum


class PurchaseStatus(Enum):
    """IPAT購入のステータス."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"

    def get_display_name(self) -> str:
        """日本語表示名を返す."""
        names = {
            PurchaseStatus.PENDING: "投票準備中",
            PurchaseStatus.SUBMITTED: "投票送信済",
            PurchaseStatus.COMPLETED: "投票完了",
            PurchaseStatus.FAILED: "投票失敗",
        }
        return names[self]
