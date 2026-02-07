"""PurchaseValidatorのテスト."""
import pytest

from src.domain.entities import Cart
from src.domain.enums import BetType
from src.domain.identifiers import UserId
from src.domain.ports import SpendingLimitProvider
from src.domain.services import PurchaseValidator
from src.domain.value_objects import (
    BetSelection,
    HorseNumbers,
    IpatBalance,
    Money,
)


class StubSpendingLimitProvider(SpendingLimitProvider):
    """テスト用スタブ."""

    def __init__(self, limit: Money | None = None, spent: Money = Money.zero()):
        self._limit = limit
        self._spent = spent

    def get_monthly_limit(self, user_id: UserId) -> Money | None:
        return self._limit

    def get_monthly_spent(self, user_id: UserId) -> Money:
        return self._spent


class TestPurchaseValidator:
    """PurchaseValidatorの単体テスト."""

    def _make_cart_with_item(self) -> Cart:
        """アイテムが1件入ったカートを生成する."""
        from src.domain.identifiers import RaceId

        cart = Cart.create(user_id=UserId("user-1"))
        cart.add_item(
            race_id=RaceId("race-1"),
            race_name="テストレース",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers.of(3),
                amount=Money.of(100),
            ),
        )
        return cart

    def _make_balance(self, bet_balance: int = 10000) -> IpatBalance:
        """テスト用IpatBalanceを生成する."""
        return IpatBalance(
            bet_dedicated_balance=bet_balance,
            settle_possible_balance=0,
            bet_balance=bet_balance,
            limit_vote_amount=100000,
        )

    def test_正常なカートでバリデーションが通る(self) -> None:
        """正常なカートと十分な残高でバリデーションが通ることを確認."""
        cart = self._make_cart_with_item()
        balance = self._make_balance(10000)
        provider = StubSpendingLimitProvider()
        user_id = UserId("user-1")

        # エラーなく通ることを確認
        PurchaseValidator.validate_purchase(cart, balance, provider, user_id)

    def test_空カートでエラー(self) -> None:
        """空カートでValueErrorが発生することを確認."""
        cart = Cart.create(user_id=UserId("user-1"))
        balance = self._make_balance(10000)
        provider = StubSpendingLimitProvider()
        user_id = UserId("user-1")

        with pytest.raises(ValueError, match="カートが空"):
            PurchaseValidator.validate_purchase(cart, balance, provider, user_id)

    def test_残高不足でエラー(self) -> None:
        """残高不足でValueErrorが発生することを確認."""
        cart = self._make_cart_with_item()
        balance = self._make_balance(50)  # 100円の買い目に対して50円
        provider = StubSpendingLimitProvider()
        user_id = UserId("user-1")

        with pytest.raises(ValueError, match="残高"):
            PurchaseValidator.validate_purchase(cart, balance, provider, user_id)

    def test_月間限度額超過でエラー(self) -> None:
        """月間限度額超過でValueErrorが発生することを確認."""
        cart = self._make_cart_with_item()
        balance = self._make_balance(10000)
        # 限度額1000円、既に950円使用、さらに100円の買い目
        provider = StubSpendingLimitProvider(
            limit=Money.of(1000),
            spent=Money.of(950),
        )
        user_id = UserId("user-1")

        with pytest.raises(ValueError, match="限度額"):
            PurchaseValidator.validate_purchase(cart, balance, provider, user_id)

    def test_月間限度額がNoneの場合はパス(self) -> None:
        """月間限度額がNone（無制限）の場合にバリデーションが通ることを確認."""
        cart = self._make_cart_with_item()
        balance = self._make_balance(10000)
        provider = StubSpendingLimitProvider(limit=None, spent=Money.of(999999))
        user_id = UserId("user-1")

        # エラーなく通ることを確認
        PurchaseValidator.validate_purchase(cart, balance, provider, user_id)

    def test_月間限度額ちょうどの場合はパス(self) -> None:
        """月間限度額ちょうどの場合にバリデーションが通ることを確認."""
        cart = self._make_cart_with_item()
        balance = self._make_balance(10000)
        # 限度額1000円、既に900円使用、さらに100円の買い目 → ちょうど1000円
        provider = StubSpendingLimitProvider(
            limit=Money.of(1000),
            spent=Money.of(900),
        )
        user_id = UserId("user-1")

        PurchaseValidator.validate_purchase(cart, balance, provider, user_id)
