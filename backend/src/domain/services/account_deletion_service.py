"""アカウント削除ドメインサービス."""
from datetime import datetime, timedelta, timezone

from ..entities import User
from ..enums import UserStatus


class AccountDeletionService:
    """アカウント削除サービス."""

    RETENTION_DAYS = 30

    @staticmethod
    def is_ready_for_permanent_deletion(user: User) -> bool:
        """物理削除の準備ができているか判定する."""
        if user.status != UserStatus.PENDING_DELETION:
            return False
        if user.deletion_requested_at is None:
            return False
        deadline = user.deletion_requested_at + timedelta(days=AccountDeletionService.RETENTION_DAYS)
        return datetime.now(timezone.utc) >= deadline

    @staticmethod
    def days_until_permanent_deletion(user: User) -> int | None:
        """物理削除までの残り日数を返す."""
        if user.status != UserStatus.PENDING_DELETION:
            return None
        if user.deletion_requested_at is None:
            return None
        deadline = user.deletion_requested_at + timedelta(days=AccountDeletionService.RETENTION_DAYS)
        remaining = (deadline - datetime.now(timezone.utc)).days
        return max(0, remaining)
