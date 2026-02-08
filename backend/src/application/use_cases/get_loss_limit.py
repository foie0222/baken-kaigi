"""負け額限度額取得ユースケース."""
from dataclasses import dataclass

from src.domain.entities import LossLimitChange, User
from src.domain.identifiers import UserId
from src.domain.ports.loss_limit_change_repository import LossLimitChangeRepository
from src.domain.ports.user_repository import UserRepository
from src.domain.value_objects import Money


class UserNotFoundError(Exception):
    """ユーザーが見つからないエラー."""

    def __init__(self, user_id: UserId) -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


@dataclass(frozen=True)
class GetLossLimitResult:
    """負け額限度額取得結果."""

    loss_limit: Money | None
    remaining_limit: Money | None
    total_loss_this_month: Money
    pending_changes: list[LossLimitChange]


class GetLossLimitUseCase:
    """負け額限度額を取得するユースケース."""

    def __init__(
        self,
        user_repository: UserRepository,
        change_repository: LossLimitChangeRepository,
    ) -> None:
        """初期化."""
        self._user_repository = user_repository
        self._change_repository = change_repository

    def execute(self, user_id: UserId) -> GetLossLimitResult:
        """負け額限度額を取得する.

        Args:
            user_id: ユーザーID

        Returns:
            負け額限度額取得結果

        Raises:
            UserNotFoundError: ユーザーが見つからない場合
        """
        user = self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        pending_changes = self._change_repository.find_pending_by_user_id(user_id)

        return GetLossLimitResult(
            loss_limit=user.loss_limit,
            remaining_limit=user.get_remaining_loss_limit(),
            total_loss_this_month=user.total_loss_this_month,
            pending_changes=pending_changes,
        )
