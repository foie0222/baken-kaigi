"""ユーザー登録ユースケース."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, timezone

from src.domain.entities import User
from src.domain.enums import AuthProvider, UserStatus
from src.domain.identifiers import UserId
from src.domain.ports.user_repository import UserRepository
from src.domain.value_objects import DateOfBirth, DisplayName, Email

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class UserAlreadyExistsError(Exception):
    """ユーザーが既に存在するエラー."""

    pass


@dataclass(frozen=True)
class RegisterUserResult:
    """ユーザー登録結果."""

    user_id: UserId
    email: Email
    display_name: DisplayName


class RegisterUserUseCase:
    """ユーザー登録ユースケース.

    Cognito Post Confirmation トリガーから呼び出される。
    """

    def __init__(self, user_repository: UserRepository) -> None:
        """初期化."""
        self._user_repository = user_repository

    def execute(
        self,
        user_id: str,
        email: str,
        display_name: str,
        date_of_birth_str: str,
        auth_provider: str = "cognito",
    ) -> RegisterUserResult:
        """ユーザーを登録する.

        Args:
            user_id: Cognito sub
            email: メールアドレス
            display_name: 表示名
            date_of_birth_str: 生年月日（YYYY-MM-DD形式）
            auth_provider: 認証プロバイダ

        Returns:
            登録結果

        Raises:
            UserAlreadyExistsError: 同一IDのユーザーが既に存在する場合
        """
        uid = UserId(user_id)

        # 既存ユーザーチェック
        existing = self._user_repository.find_by_id(uid)
        if existing is not None:
            raise UserAlreadyExistsError(f"User already exists: {user_id}")

        # 値オブジェクト変換
        email_vo = Email(email)
        display_name_vo = DisplayName(display_name)

        if not _DATE_PATTERN.match(date_of_birth_str):
            raise ValueError(
                f"Invalid date format: {date_of_birth_str!r} (expected YYYY-MM-DD)"
            )
        parts = date_of_birth_str.split("-")
        dob = DateOfBirth(date_type(int(parts[0]), int(parts[1]), int(parts[2])))

        now = datetime.now(timezone.utc)
        provider = AuthProvider(auth_provider)

        user = User(
            user_id=uid,
            email=email_vo,
            display_name=display_name_vo,
            date_of_birth=dob,
            terms_accepted_at=now,
            privacy_accepted_at=now,
            auth_provider=provider,
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        self._user_repository.save(user)

        return RegisterUserResult(
            user_id=uid,
            email=email_vo,
            display_name=display_name_vo,
        )
