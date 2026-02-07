"""IpatBalanceのテスト."""
import pytest

from src.domain.value_objects import IpatBalance


class TestIpatBalance:
    """IpatBalanceの単体テスト."""

    def test_正常な値で生成できる(self) -> None:
        """正常な値でIpatBalanceを生成できることを確認."""
        balance = IpatBalance(
            bet_dedicated_balance=10000,
            settle_possible_balance=5000,
            bet_balance=15000,
            limit_vote_amount=100000,
        )
        assert balance.bet_dedicated_balance == 10000
        assert balance.settle_possible_balance == 5000
        assert balance.bet_balance == 15000
        assert balance.limit_vote_amount == 100000

    def test_ゼロの残高で生成できる(self) -> None:
        """ゼロの残高でIpatBalanceを生成できることを確認."""
        balance = IpatBalance(
            bet_dedicated_balance=0,
            settle_possible_balance=0,
            bet_balance=0,
            limit_vote_amount=0,
        )
        assert balance.bet_balance == 0

    def test_不変オブジェクトである(self) -> None:
        """IpatBalanceは不変（frozen）であることを確認."""
        balance = IpatBalance(
            bet_dedicated_balance=10000,
            settle_possible_balance=5000,
            bet_balance=15000,
            limit_vote_amount=100000,
        )
        with pytest.raises(AttributeError):
            balance.bet_balance = 20000  # type: ignore
