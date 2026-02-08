"""ユーザーエンティティ."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..enums import AuthProvider, UserStatus
from ..identifiers import UserId
from ..value_objects import DateOfBirth, DisplayName, Email, Money


@dataclass
class User:
    """ユーザーエンティティ."""

    user_id: UserId
    email: Email
    display_name: DisplayName
    date_of_birth: DateOfBirth
    terms_accepted_at: datetime
    privacy_accepted_at: datetime
    auth_provider: AuthProvider
    status: UserStatus = UserStatus.ACTIVE
    deletion_requested_at: datetime | None = None
    loss_limit: Money | None = None
    total_loss_this_month: Money = field(default_factory=Money.zero)
    loss_limit_set_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_display_name(self, display_name: DisplayName) -> None:
        """表示名を更新する."""
        self.display_name = display_name
        self.updated_at = datetime.now(timezone.utc)

    def update_email(self, email: Email) -> None:
        """メールアドレスを更新する."""
        self.email = email
        self.updated_at = datetime.now(timezone.utc)

    def request_deletion(self) -> None:
        """アカウント削除をリクエストする."""
        if self.status == UserStatus.DELETED:
            raise ValueError("User is already deleted")
        self.status = UserStatus.PENDING_DELETION
        self.deletion_requested_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def cancel_deletion(self) -> None:
        """アカウント削除をキャンセルする."""
        if self.status != UserStatus.PENDING_DELETION:
            raise ValueError("User is not pending deletion")
        self.status = UserStatus.ACTIVE
        self.deletion_requested_at = None
        self.updated_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """アクティブかどうか."""
        return self.status == UserStatus.ACTIVE

    def is_pending_deletion(self) -> bool:
        """削除保留中かどうか."""
        return self.status == UserStatus.PENDING_DELETION

    def set_loss_limit(self, amount: Money) -> None:
        """月間負け額限度額を設定する."""
        if amount.value <= 0:
            raise ValueError("Loss limit must be positive")
        self.loss_limit = amount
        self.loss_limit_set_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def get_remaining_loss_limit(self) -> Money | None:
        """残り負け額限度額を取得する."""
        if self.loss_limit is None:
            return None
        remaining = self.loss_limit.value - self.total_loss_this_month.value
        if remaining < 0:
            return Money.zero()
        return Money.of(remaining)

    def record_loss(self, amount: Money) -> None:
        """損失を記録する."""
        self.total_loss_this_month = self.total_loss_this_month.add(amount)
        self.updated_at = datetime.now(timezone.utc)

    def reset_monthly_loss(self) -> None:
        """月初に累計損失額をリセットする."""
        self.total_loss_this_month = Money.zero()
        self.updated_at = datetime.now(timezone.utc)
