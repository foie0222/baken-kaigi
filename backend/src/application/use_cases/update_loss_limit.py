"""負け額限度額変更ユースケース."""
from dataclasses import dataclass

from src.domain.constants import LOSS_LIMIT_MAX, LOSS_LIMIT_MIN
from src.domain.entities import LossLimitChange
from src.domain.enums import LossLimitChangeType
from src.domain.identifiers import UserId
from src.domain.ports.loss_limit_change_repository import LossLimitChangeRepository
from src.domain.ports.user_repository import UserRepository
from src.domain.services import LossLimitService
from src.domain.value_objects import Money


class UserNotFoundError(Exception):
    """ユーザーが見つからないエラー."""

    def __init__(self, user_id: UserId) -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


class LossLimitNotSetError(Exception):
    """限度額が未設定のエラー."""

    pass


class InvalidLossLimitAmountError(Exception):
    """無効な限度額のエラー."""

    pass


class PendingChangeExistsError(Exception):
    """保留中の変更リクエストが存在するエラー."""

    pass


@dataclass(frozen=True)
class UpdateLossLimitResult:
    """限度額変更結果."""

    change: LossLimitChange
    applied_immediately: bool


class UpdateLossLimitUseCase:
    """負け額限度額を変更するユースケース."""

    def __init__(
        self,
        user_repository: UserRepository,
        change_repository: LossLimitChangeRepository,
    ) -> None:
        """初期化."""
        self._user_repository = user_repository
        self._change_repository = change_repository
        self._loss_limit_service = LossLimitService()

    def execute(self, user_id: UserId, new_amount: int) -> UpdateLossLimitResult:
        """限度額を変更する.

        Args:
            user_id: ユーザーID
            new_amount: 新しい限度額（円）

        Returns:
            変更結果

        Raises:
            UserNotFoundError: ユーザーが見つからない場合
            LossLimitNotSetError: 限度額が未設定の場合
            InvalidLossLimitAmountError: 無効な金額の場合
        """
        if new_amount < LOSS_LIMIT_MIN or new_amount > LOSS_LIMIT_MAX:
            raise InvalidLossLimitAmountError(
                f"Loss limit must be between {LOSS_LIMIT_MIN} and {LOSS_LIMIT_MAX}"
            )

        user = self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        if user.loss_limit is None:
            raise LossLimitNotSetError("Loss limit is not set yet")

        pending = self._change_repository.find_pending_by_user_id(user_id)
        if pending:
            raise PendingChangeExistsError(
                "A pending change request already exists"
            )

        new_limit = Money.of(new_amount)
        change = self._loss_limit_service.request_change(user, new_limit)

        self._user_repository.save(user)
        self._change_repository.save(change)

        applied_immediately = change.change_type == LossLimitChangeType.DECREASE

        return UpdateLossLimitResult(
            change=change,
            applied_immediately=applied_immediately,
        )
