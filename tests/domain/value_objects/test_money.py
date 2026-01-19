"""Moneyのテスト."""
import pytest

from src.domain.value_objects import Money


class TestMoney:
    """Moneyの単体テスト."""

    def test_正の金額で生成できる(self) -> None:
        """正の金額を指定してMoneyを生成できることを確認."""
        money = Money(1000)
        assert money.value == 1000

    def test_ゼロで生成できる(self) -> None:
        """ゼロ円のMoneyを生成できることを確認."""
        money = Money(0)
        assert money.value == 0

    def test_負の金額で生成するとエラー(self) -> None:
        """負の金額を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Money(-100)

    def test_ofで生成できる(self) -> None:
        """ofメソッドでMoneyを生成できることを確認."""
        money = Money.of(500)
        assert money.value == 500

    def test_zeroでゼロ円を生成できる(self) -> None:
        """zeroメソッドでゼロ円のMoneyを生成できることを確認."""
        money = Money.zero()
        assert money.value == 0

    def test_from_presetで100円を生成できる(self) -> None:
        """from_presetでプリセット値100円を生成できることを確認."""
        money = Money.from_preset(100)
        assert money.value == 100

    def test_from_presetで無効な値はエラー(self) -> None:
        """from_presetに無効な値を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="Invalid preset"):
            Money.from_preset(200)

    def test_addで加算できる(self) -> None:
        """addメソッドで金額を加算できることを確認."""
        m1 = Money(1000)
        m2 = Money(500)
        result = m1.add(m2)
        assert result.value == 1500

    def test_subtractで減算できる(self) -> None:
        """subtractメソッドで金額を減算できることを確認."""
        m1 = Money(1000)
        m2 = Money(300)
        result = m1.subtract(m2)
        assert result.value == 700

    def test_subtractで結果が負になるとエラー(self) -> None:
        """subtractの結果が負になるとValueErrorが発生することを確認."""
        m1 = Money(100)
        m2 = Money(500)
        with pytest.raises(ValueError, match="negative"):
            m1.subtract(m2)

    def test_multiplyで乗算できる(self) -> None:
        """multiplyメソッドで金額を乗算できることを確認."""
        money = Money(100)
        result = money.multiply(3)
        assert result.value == 300

    def test_multiplyで負の係数はエラー(self) -> None:
        """multiplyに負の係数を指定するとValueErrorが発生することを確認."""
        money = Money(100)
        with pytest.raises(ValueError, match="cannot be negative"):
            money.multiply(-1)

    def test_is_greater_thanで大きい場合True(self) -> None:
        """is_greater_thanで大きい場合にTrueが返ることを確認."""
        m1 = Money(1000)
        m2 = Money(500)
        assert m1.is_greater_than(m2) is True

    def test_is_greater_thanで小さい場合False(self) -> None:
        """is_greater_thanで小さい場合にFalseが返ることを確認."""
        m1 = Money(500)
        m2 = Money(1000)
        assert m1.is_greater_than(m2) is False

    def test_is_less_than_or_equalで以下の場合True(self) -> None:
        """is_less_than_or_equalで以下の場合にTrueが返ることを確認."""
        m1 = Money(500)
        m2 = Money(1000)
        assert m1.is_less_than_or_equal(m2) is True

    def test_is_valid_bet_amountで有効な金額はTrue(self) -> None:
        """is_valid_bet_amountで100円以上かつ100円単位の場合Trueを確認."""
        assert Money(100).is_valid_bet_amount() is True
        assert Money(500).is_valid_bet_amount() is True
        assert Money(1000).is_valid_bet_amount() is True

    def test_is_valid_bet_amountで100円未満はFalse(self) -> None:
        """is_valid_bet_amountで100円未満の場合Falseを確認."""
        assert Money(50).is_valid_bet_amount() is False
        assert Money(0).is_valid_bet_amount() is False

    def test_is_valid_bet_amountで100円単位でない場合はFalse(self) -> None:
        """is_valid_bet_amountで100円単位でない場合Falseを確認."""
        assert Money(150).is_valid_bet_amount() is False

    def test_formatで円記号付きカンマ区切り(self) -> None:
        """formatメソッドで円記号付きカンマ区切りの文字列を確認."""
        assert Money(1000).format() == "¥1,000"
        assert Money(10000).format() == "¥10,000"

    def test_不変オブジェクトである(self) -> None:
        """Moneyは不変（frozen）であることを確認."""
        money = Money(100)
        with pytest.raises(AttributeError):
            money.value = 200  # type: ignore
