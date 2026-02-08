"""インメモリ負け額限度額変更リポジトリ実装."""
from src.domain.entities import LossLimitChange
from src.domain.enums import LossLimitChangeStatus
from src.domain.identifiers import LossLimitChangeId, UserId
from src.domain.ports.loss_limit_change_repository import LossLimitChangeRepository


class InMemoryLossLimitChangeRepository(LossLimitChangeRepository):
    """インメモリ負け額限度額変更リポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._changes: dict[str, LossLimitChange] = {}

    def save(self, change: LossLimitChange) -> None:
        """変更リクエストを保存する."""
        self._changes[change.change_id.value] = change

    def find_by_id(self, change_id: LossLimitChangeId) -> LossLimitChange | None:
        """変更リクエストIDで検索する."""
        return self._changes.get(change_id.value)

    def find_pending_by_user_id(self, user_id: UserId) -> list[LossLimitChange]:
        """ユーザーIDで保留中の変更リクエストを検索する."""
        return [
            change
            for change in self._changes.values()
            if change.user_id == user_id
            and change.status == LossLimitChangeStatus.PENDING
        ]

    def find_by_user_id(self, user_id: UserId) -> list[LossLimitChange]:
        """ユーザーIDで変更リクエストを検索する."""
        return [
            change
            for change in self._changes.values()
            if change.user_id == user_id
        ]
