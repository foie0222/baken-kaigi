"""ユーザーステータスの列挙型."""
from enum import Enum


class UserStatus(str, Enum):
    """ユーザーステータス."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_DELETION = "pending_deletion"
    DELETED = "deleted"
