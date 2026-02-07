"""ユーザープロフィール更新ユースケース."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.identifiers import UserId
from src.domain.ports.user_repository import UserRepository
from src.domain.value_objects import DisplayName, Email

from .get_user_profile import UserNotFoundError


@dataclass(frozen=True)
class UpdateUserProfileResult:
    """プロフィール更新結果."""

    user_id: UserId
    email: Email
    display_name: DisplayName


class UpdateUserProfileUseCase:
    """ユーザープロフィール更新ユースケース."""

    def __init__(self, user_repository: UserRepository) -> None:
        """初期化."""
        self._user_repository = user_repository

    def execute(
        self,
        user_id: UserId,
        display_name: str | None = None,
        email: str | None = None,
    ) -> UpdateUserProfileResult:
        """プロフィールを更新する.

        Args:
            user_id: ユーザーID
            display_name: 新しい表示名（省略時は変更なし）
            email: 新しいメールアドレス（省略時は変更なし）

        Returns:
            更新結果

        Raises:
            UserNotFoundError: ユーザーが見つからない場合
        """
        user = self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")

        if display_name is not None:
            user.update_display_name(DisplayName(display_name))

        if email is not None:
            user.update_email(Email(email))

        self._user_repository.save(user)

        return UpdateUserProfileResult(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
        )
