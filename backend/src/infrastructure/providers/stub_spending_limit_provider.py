"""月間支出制限プロバイダーのスタブ実装."""
from src.domain.identifiers import UserId
from src.domain.ports import SpendingLimitProvider
from src.domain.value_objects import Money


class StubSpendingLimitProvider(SpendingLimitProvider):
    """月間支出制限プロバイダーのスタブ（常に無制限）."""

    def get_monthly_limit(self, user_id: UserId) -> Money | None:
        """月間限度額を取得する（常にNone=無制限）."""
        return None

    def get_monthly_spent(self, user_id: UserId) -> Money:
        """当月の支出額を取得する（常にゼロ）."""
        return Money.zero()
