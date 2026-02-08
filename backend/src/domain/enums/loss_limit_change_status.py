"""負け額限度額変更ステータスの列挙型."""
from enum import Enum


class LossLimitChangeStatus(Enum):
    """負け額限度額変更リクエストの状態."""

    PENDING = "pending"  # 待機中（増額時の7日間待機）
    APPROVED = "approved"  # 承認済み
    REJECTED = "rejected"  # 却下済み
