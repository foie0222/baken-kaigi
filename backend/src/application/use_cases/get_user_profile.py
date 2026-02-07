"""ユーザープロフィール取得ユースケース."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.enums import AuthProvider, UserStatus
from src.domain.identifiers import UserId
from src.domain.ports.user_repository import UserRepository
from src.domain.value_objects import DateOfBirth, DisplayName, Email


class UserNotFoundError(Exception):
    """ユーザーが見つからないエラー."""

    pass


@dataclass(frozen=True)
class UserProfileResult:
    """ユーザープロフィール結果."""

    user_id: UserId
    email: Email
    display_name: DisplayName
    date_of_birth: DateOfBirth
    auth_provider: AuthProvider
    status: UserStatus
    created_at: datetime


class GetUserProfileUseCase:
    """ユーザープロフィール取得ユースケース."""

    def __init__(self, user_repository: UserRepository) -> None:
        """初期化."""
        self._user_repository = user_repository

    def execute(self, user_id: UserId) -> UserProfileResult:
        """ユーザープロフィールを取得する.

        Args:
            user_id: ユーザーID

        Returns:
            プロフィール情報

        Raises:
            UserNotFoundError: ユーザーが見つからない場合
        """
        user = self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")

        return UserProfileResult(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            date_of_birth=user.date_of_birth,
            auth_provider=user.auth_provider,
            status=user.status,
            created_at=user.created_at,
        )
