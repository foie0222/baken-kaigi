"""購入バリデーションドメインサービス."""
from ..entities import Cart
from ..identifiers import UserId
from ..ports.spending_limit_provider import SpendingLimitProvider
from ..value_objects import IpatBalance


class PurchaseValidator:
    """購入前のバリデーションを行うサービス."""

    @staticmethod
    def validate_purchase(
        cart: Cart,
        balance: IpatBalance,
        spending_limit_provider: SpendingLimitProvider,
        user_id: UserId,
    ) -> None:
        """購入のバリデーションを実行する."""
        if cart.is_empty():
            raise ValueError("カートが空です")

        total = cart.get_total_amount()
        if total.value > balance.bet_balance:
            raise ValueError("残高が不足しています")

        monthly_limit = spending_limit_provider.get_monthly_limit(user_id)
        if monthly_limit is not None:
            monthly_spent = spending_limit_provider.get_monthly_spent(user_id)
            if monthly_spent.value + total.value > monthly_limit.value:
                raise ValueError("月間限度額を超過します")
