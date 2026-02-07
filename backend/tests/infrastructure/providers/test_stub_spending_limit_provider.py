"""StubSpendingLimitProvider のテスト."""
import unittest

from src.domain.identifiers import UserId
from src.domain.value_objects import Money
from src.infrastructure.providers.stub_spending_limit_provider import (
    StubSpendingLimitProvider,
)


class TestStubSpendingLimitProvider(unittest.TestCase):
    """StubSpendingLimitProvider のテスト."""

    def setUp(self) -> None:
        self.provider = StubSpendingLimitProvider()
        self.user_id = UserId("user-001")

    def test_月間限度額は常にNone(self) -> None:
        result = self.provider.get_monthly_limit(self.user_id)
        assert result is None

    def test_月間支出額は常にゼロ(self) -> None:
        result = self.provider.get_monthly_spent(self.user_id)
        assert result == Money.zero()
