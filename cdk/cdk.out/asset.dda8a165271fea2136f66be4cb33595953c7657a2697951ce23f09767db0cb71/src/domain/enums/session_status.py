"""セッション状態の列挙型."""
from enum import Enum


class SessionStatus(Enum):
    """相談セッションの状態."""

    NOT_STARTED = "not_started"  # 未開始
    IN_PROGRESS = "in_progress"  # 進行中
    COMPLETED = "completed"  # 完了
