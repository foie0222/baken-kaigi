"""負け額限度額設定ユースケース."""
from dataclasses import dataclass

from src.domain.constants import LOSS_LIMIT_MAX, LOSS_LIMIT_MIN
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


class LossLimitAlreadySetError(Exception):
    """既に限度額が設定済みのエラー."""

    pass


class InvalidLossLimitAmountError(Exception):
    """無効な限度額のエラー."""

    pass


@dataclass(frozen=True)
class SetLossLimitResult:
    """限度額設定結果."""

    loss_limit: Money


class SetLossLimitUseCase:
    """初回の負け額限度額を設定するユースケース."""

    def __init__(
        self,
        user_repository: UserRepository,
        change_repository: LossLimitChangeRepository,
    ) -> None:
        """初期化."""
        self._user_repository = user_repository
        self._change_repository = change_repository
        self._loss_limit_service = LossLimitService()

    def execute(self, user_id: UserId, amount: int) -> SetLossLimitResult:
        """限度額を設定する.

        Args:
            user_id: ユーザーID
            amount: 限度額（円）

        Returns:
            設定結果

        Raises:
            UserNotFoundError: ユーザーが見つからない場合
            LossLimitAlreadySetError: 既に限度額が設定済みの場合
            InvalidLossLimitAmountError: 無効な金額の場合
        """
        if amount < LOSS_LIMIT_MIN or amount > LOSS_LIMIT_MAX:
            raise InvalidLossLimitAmountError(
                f"Loss limit must be between {LOSS_LIMIT_MIN} and {LOSS_LIMIT_MAX}"
            )

        user = self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        if user.loss_limit is not None:
            raise LossLimitAlreadySetError("Loss limit is already set")

        new_limit = Money.of(amount)
        change = self._loss_limit_service.request_change(user, new_limit)

        self._user_repository.save(user)
        self._change_repository.save(change)

        return SetLossLimitResult(loss_limit=new_limit)
