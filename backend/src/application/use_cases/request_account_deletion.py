"""アカウント削除リクエストユースケース."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.identifiers import UserId
from src.domain.ports.user_repository import UserRepository
from src.domain.services import AccountDeletionService

from .get_user_profile import UserNotFoundError


@dataclass(frozen=True)
class AccountDeletionResult:
    """アカウント削除リクエスト結果."""

    user_id: UserId
    deletion_requested_at: datetime
    days_until_permanent_deletion: int


class RequestAccountDeletionUseCase:
    """アカウント削除リクエストユースケース."""

    def __init__(self, user_repository: UserRepository) -> None:
        """初期化."""
        self._user_repository = user_repository

    def execute(self, user_id: UserId) -> AccountDeletionResult:
        """アカウント削除をリクエストする.

        Args:
            user_id: ユーザーID

        Returns:
            削除リクエスト結果

        Raises:
            UserNotFoundError: ユーザーが見つからない場合
        """
        user = self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")

        user.request_deletion()
        self._user_repository.save(user)

        days = AccountDeletionService.days_until_permanent_deletion(user)

        return AccountDeletionResult(
            user_id=user.user_id,
            deletion_requested_at=user.deletion_requested_at,  # type: ignore
            days_until_permanent_deletion=days if days is not None else AccountDeletionService.RETENTION_DAYS,
        )
