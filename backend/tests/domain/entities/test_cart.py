"""Cartのテスト."""
import pytest

from src.domain.value_objects import BetSelection
from src.domain.enums import BetType
from src.domain.entities import Cart
from src.domain.value_objects import HorseNumbers
from src.domain.value_objects import Money
from src.domain.identifiers import RaceId
from src.domain.identifiers import UserId


class TestCart:
    """Cartの単体テスト."""

    def test_createで空のカートを生成(self) -> None:
        """createメソッドで空のカートを生成できることを確認."""
        cart = Cart.create()
        assert cart.is_empty() is True
        assert cart.get_item_count() == 0

    def test_createでユーザー紐付きカートを生成(self) -> None:
        """createメソッドでユーザー紐付きカートを生成できることを確認."""
        cart = Cart.create(user_id=UserId("user-1"))
        assert cart.user_id.value == "user-1"

    def test_add_itemでアイテムを追加(self) -> None:
        """add_itemでアイテムをカートに追加できることを確認."""
        cart = Cart.create()
        bet = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(5),
            amount=Money(1000),
        )
        item = cart.add_item(
            race_id=RaceId("race-1"),
            race_name="日本ダービー",
            bet_selection=bet,
        )
        assert cart.get_item_count() == 1
        assert item.race_name == "日本ダービー"

    def test_add_itemで複数アイテムを追加(self) -> None:
        """add_itemで複数アイテムを追加できることを確認."""
        cart = Cart.create()
        bet1 = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        bet2 = BetSelection(BetType.PLACE, HorseNumbers.of(2), Money(200))
        cart.add_item(RaceId("r1"), "レース1", bet1)
        cart.add_item(RaceId("r2"), "レース2", bet2)
        assert cart.get_item_count() == 2

    def test_remove_itemでアイテムを削除(self) -> None:
        """remove_itemで指定アイテムを削除できることを確認."""
        cart = Cart.create()
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        item = cart.add_item(RaceId("r1"), "レース1", bet)
        result = cart.remove_item(item.item_id)
        assert result is True
        assert cart.is_empty() is True

    def test_remove_itemで存在しないIDはFalse(self) -> None:
        """remove_itemで存在しないIDを指定するとFalseが返ることを確認."""
        cart = Cart.create()
        from src.domain.identifiers import ItemId
        result = cart.remove_item(ItemId("nonexistent"))
        assert result is False

    def test_clearで全アイテムを削除(self) -> None:
        """clearで全アイテムを削除できることを確認."""
        cart = Cart.create()
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        cart.add_item(RaceId("r1"), "レース1", bet)
        cart.add_item(RaceId("r2"), "レース2", bet)
        cart.clear()
        assert cart.is_empty() is True

    def test_get_total_amountで合計金額を取得(self) -> None:
        """get_total_amountで全アイテムの合計金額を取得できることを確認."""
        cart = Cart.create()
        cart.add_item(RaceId("r1"), "R1", BetSelection(BetType.WIN, HorseNumbers.of(1), Money(1000)))
        cart.add_item(RaceId("r2"), "R2", BetSelection(BetType.PLACE, HorseNumbers.of(2), Money(500)))
        assert cart.get_total_amount().value == 1500

    def test_get_total_amountで空カートはゼロ(self) -> None:
        """get_total_amountで空カートの場合ゼロ円が返ることを確認."""
        cart = Cart.create()
        assert cart.get_total_amount().value == 0

    def test_get_itemsで防御的コピーを取得(self) -> None:
        """get_itemsで防御的コピーが返ることを確認."""
        cart = Cart.create()
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        cart.add_item(RaceId("r1"), "レース1", bet)
        items = cart.get_items()
        items.clear()  # 外部でクリアしても
        assert cart.get_item_count() == 1  # 内部は影響なし

    def test_get_itemで指定IDのアイテムを取得(self) -> None:
        """get_itemで指定IDのアイテムを取得できることを確認."""
        cart = Cart.create()
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        item = cart.add_item(RaceId("r1"), "レース1", bet)
        found = cart.get_item(item.item_id)
        assert found is not None
        assert found.race_name == "レース1"

    def test_get_itemで存在しないIDはNone(self) -> None:
        """get_itemで存在しないIDを指定するとNoneが返ることを確認."""
        cart = Cart.create()
        from src.domain.identifiers import ItemId
        assert cart.get_item(ItemId("nonexistent")) is None

    def test_associate_userでユーザーを紐付け(self) -> None:
        """associate_userでユーザーを紐付けできることを確認."""
        cart = Cart.create()
        cart.associate_user(UserId("user-1"))
        assert cart.user_id.value == "user-1"

    def test_associate_userで既に紐付いている場合エラー(self) -> None:
        """associate_userで既にユーザーが紐付いている場合エラーになることを確認."""
        cart = Cart.create(user_id=UserId("user-1"))
        with pytest.raises(ValueError, match="already associated"):
            cart.associate_user(UserId("user-2"))

    def test_updated_atが操作後に更新される(self) -> None:
        """操作後にupdated_atが更新されることを確認."""
        cart = Cart.create()
        initial = cart.updated_at
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        cart.add_item(RaceId("r1"), "レース1", bet)
        assert cart.updated_at >= initial
