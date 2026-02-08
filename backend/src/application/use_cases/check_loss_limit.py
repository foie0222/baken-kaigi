"""負け額限度額チェックユースケース."""
from dataclasses import dataclass

from src.domain.enums import WarningLevel
from src.domain.identifiers import UserId
from src.domain.ports.user_repository import UserRepository
from src.domain.services import LossLimitService
from src.domain.value_objects import Money


class UserNotFoundError(Exception):
    """ユーザーが見つからないエラー."""

    def __init__(self, user_id: UserId) -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


@dataclass(frozen=True)
class CheckLossLimitResult:
    """限度額チェック結果."""

    can_purchase: bool
    remaining_amount: Money | None
    warning_level: WarningLevel
    message: str


class CheckLossLimitUseCase:
    """購入可否をチェックするユースケース."""

    def __init__(self, user_repository: UserRepository) -> None:
        """初期化."""
        self._user_repository = user_repository
        self._loss_limit_service = LossLimitService()

    def execute(self, user_id: UserId, amount: int) -> CheckLossLimitResult:
        """購入可否をチェックする.

        Args:
            user_id: ユーザーID
            amount: 購入金額（円）

        Returns:
            チェック結果

        Raises:
            UserNotFoundError: ユーザーが見つからない場合
        """
        user = self._user_repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        bet_amount = Money.of(amount)
        result = self._loss_limit_service.check_limit(user, bet_amount)

        return CheckLossLimitResult(
            can_purchase=result.can_purchase,
            remaining_amount=result.remaining_amount,
            warning_level=result.warning_level,
            message=result.message,
        )
