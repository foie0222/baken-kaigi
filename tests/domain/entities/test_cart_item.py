"""CartItemのテスト."""
from datetime import datetime

import pytest

from src.domain.value_objects import BetSelection
from src.domain.enums import BetType
from src.domain.entities import CartItem
from src.domain.value_objects import HorseNumbers
from src.domain.value_objects import Money
from src.domain.identifiers import RaceId


class TestCartItem:
    """CartItemの単体テスト."""

    def test_createで生成できる(self) -> None:
        """createメソッドでCartItemを生成できることを確認."""
        bet = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(5),
            amount=Money(1000),
        )
        item = CartItem.create(
            race_id=RaceId("2024010101"),
            race_name="日本ダービー",
            bet_selection=bet,
        )
        assert item.race_name == "日本ダービー"
        assert item.item_id is not None

    def test_createでitem_idが自動生成される(self) -> None:
        """createメソッドでitem_idが自動生成されることを確認."""
        bet = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(1),
            amount=Money(100),
        )
        item = CartItem.create(
            race_id=RaceId("race-1"),
            race_name="テスト",
            bet_selection=bet,
        )
        assert len(item.item_id.value) == 36  # UUID形式

    def test_空のレース名でエラー(self) -> None:
        """空のレース名を指定するとValueErrorが発生することを確認."""
        bet = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(1),
            amount=Money(100),
        )
        with pytest.raises(ValueError, match="cannot be empty"):
            CartItem.create(
                race_id=RaceId("race-1"),
                race_name="",
                bet_selection=bet,
            )

    def test_get_amountで金額を取得(self) -> None:
        """get_amountで金額を取得できることを確認."""
        bet = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(1),
            amount=Money(500),
        )
        item = CartItem.create(
            race_id=RaceId("race-1"),
            race_name="テスト",
            bet_selection=bet,
        )
        assert item.get_amount().value == 500

    def test_get_bet_typeで券種を取得(self) -> None:
        """get_bet_typeで券種を取得できることを確認."""
        bet = BetSelection(
            bet_type=BetType.QUINELLA,
            horse_numbers=HorseNumbers.of(1, 2),
            amount=Money(100),
        )
        item = CartItem.create(
            race_id=RaceId("race-1"),
            race_name="テスト",
            bet_selection=bet,
        )
        assert item.get_bet_type() == BetType.QUINELLA

    def test_get_selected_numbersで馬番を取得(self) -> None:
        """get_selected_numbersで選択馬番を取得できることを確認."""
        bet = BetSelection(
            bet_type=BetType.TRIO,
            horse_numbers=HorseNumbers.of(1, 3, 5),
            amount=Money(100),
        )
        item = CartItem.create(
            race_id=RaceId("race-1"),
            race_name="テスト",
            bet_selection=bet,
        )
        assert item.get_selected_numbers().to_list() == [1, 3, 5]

    def test_不変オブジェクトである(self) -> None:
        """CartItemは不変（frozen）であることを確認."""
        bet = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(1),
            amount=Money(100),
        )
        item = CartItem.create(
            race_id=RaceId("race-1"),
            race_name="テスト",
            bet_selection=bet,
        )
        with pytest.raises(AttributeError):
            item.race_name = "変更"  # type: ignore
