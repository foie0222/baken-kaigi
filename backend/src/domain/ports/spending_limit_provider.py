"""月間支出制限プロバイダーインターフェース."""
from abc import ABC, abstractmethod

from ..identifiers import UserId
from ..value_objects import Money


class SpendingLimitProvider(ABC):
    """月間支出制限の管理インターフェース."""

    @abstractmethod
    def get_monthly_limit(self, user_id: UserId) -> Money | None:
        """月間限度額を取得する（Noneで無制限）."""
        pass

    @abstractmethod
    def get_monthly_spent(self, user_id: UserId) -> Money:
        """当月の支出額を取得する."""
        pass
