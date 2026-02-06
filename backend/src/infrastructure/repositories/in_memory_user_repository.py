"""インメモリユーザーリポジトリ実装."""
from src.domain.entities import User
from src.domain.identifiers import UserId
from src.domain.ports.user_repository import UserRepository
from src.domain.value_objects import Email


class InMemoryUserRepository(UserRepository):
    """インメモリユーザーリポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._users: dict[str, User] = {}

    def save(self, user: User) -> None:
        """ユーザーを保存する."""
        self._users[user.user_id.value] = user

    def find_by_id(self, user_id: UserId) -> User | None:
        """ユーザーIDで検索する."""
        return self._users.get(user_id.value)

    def find_by_email(self, email: Email) -> User | None:
        """メールアドレスで検索する."""
        for user in self._users.values():
            if user.email.value == email.value:
                return user
        return None

    def delete(self, user_id: UserId) -> None:
        """ユーザーを削除する."""
        self._users.pop(user_id.value, None)
