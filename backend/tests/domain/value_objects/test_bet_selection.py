"""BetSelectionのテスト."""
import pytest

from src.domain.value_objects import BetSelection
from src.domain.enums import BetType
from src.domain.value_objects import HorseNumbers
from src.domain.value_objects import Money


class TestBetSelection:
    """BetSelectionの単体テスト."""

    def test_有効な買い目を生成できる_単勝(self) -> None:
        """単勝の有効な買い目を生成できることを確認."""
        selection = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(5),
            amount=Money(100),
        )
        assert selection.bet_type == BetType.WIN
        assert selection.horse_numbers.count() == 1
        assert selection.amount.value == 100

    def test_有効な買い目を生成できる_三連単(self) -> None:
        """三連単の有効な買い目を生成できることを確認."""
        selection = BetSelection(
            bet_type=BetType.TRIFECTA,
            horse_numbers=HorseNumbers.of(1, 2, 3),
            amount=Money(500),
        )
        assert selection.bet_type == BetType.TRIFECTA
        assert selection.horse_numbers.count() == 3

    def test_馬番数が不足するとエラー(self) -> None:
        """券種に対して馬番数が不足するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="requires 2 horses"):
            BetSelection(
                bet_type=BetType.QUINELLA,
                horse_numbers=HorseNumbers.of(1),  # 馬連は2頭必要
                amount=Money(100),
            )

    def test_馬番数が超過するとエラー(self) -> None:
        """券種に対して馬番数が超過するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="requires 1 horses"):
            BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers.of(1, 2),  # 単勝は1頭のみ
                amount=Money(100),
            )

    def test_金額が100円未満でエラー(self) -> None:
        """金額が100円未満だとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="at least 100 yen"):
            BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers.of(1),
                amount=Money(50),
            )

    def test_金額が100円単位でないとエラー(self) -> None:
        """金額が100円単位でないとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="100 yen increments"):
            BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers.of(1),
                amount=Money(150),
            )

    def test_createで生成できる(self) -> None:
        """createメソッドで買い目を生成できることを確認."""
        selection = BetSelection.create(
            bet_type=BetType.PLACE,
            horse_numbers=HorseNumbers.of(3),
            amount=Money(200),
        )
        assert selection.bet_type == BetType.PLACE

    def test_is_validで有効な買い目はTrue(self) -> None:
        """is_validで有効な買い目に対してTrueが返ることを確認."""
        selection = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(1),
            amount=Money(100),
        )
        assert selection.is_valid() is True

    def test_get_required_countで必要頭数を取得(self) -> None:
        """get_required_countで券種の必要頭数を取得できることを確認."""
        selection = BetSelection(
            bet_type=BetType.TRIO,
            horse_numbers=HorseNumbers.of(1, 2, 3),
            amount=Money(100),
        )
        assert selection.get_required_count() == 3

    def test_get_amountで金額を取得(self) -> None:
        """get_amountで金額を取得できることを確認."""
        selection = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(1),
            amount=Money(1000),
        )
        assert selection.get_amount().value == 1000

    def test_get_bet_typeで券種を取得(self) -> None:
        """get_bet_typeで券種を取得できることを確認."""
        selection = BetSelection(
            bet_type=BetType.EXACTA,
            horse_numbers=HorseNumbers.of(1, 2),
            amount=Money(100),
        )
        assert selection.get_bet_type() == BetType.EXACTA

    def test_不変オブジェクトである(self) -> None:
        """BetSelectionは不変（frozen）であることを確認."""
        selection = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(1),
            amount=Money(100),
        )
        with pytest.raises(AttributeError):
            selection.amount = Money(200)  # type: ignore
