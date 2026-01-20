"""RemoveFromCartUseCaseのテスト."""
import pytest

from src.domain.entities import Cart
from src.domain.enums import BetType
from src.domain.identifiers import CartId, ItemId, RaceId, UserId
from src.domain.ports import CartRepository
from src.domain.value_objects import BetSelection, HorseNumbers, Money


class MockCartRepository(CartRepository):
    """テスト用のモックリポジトリ."""

    def __init__(self) -> None:
        self._carts: dict[str, Cart] = {}
        self._carts_by_user: dict[str, Cart] = {}

    def save(self, cart: Cart) -> None:
        self._carts[str(cart.cart_id)] = cart
        if cart.user_id:
            self._carts_by_user[str(cart.user_id)] = cart

    def find_by_id(self, cart_id: CartId) -> Cart | None:
        return self._carts.get(str(cart_id))

    def find_by_user_id(self, user_id: UserId) -> Cart | None:
        return self._carts_by_user.get(str(user_id))

    def delete(self, cart_id: CartId) -> None:
        if str(cart_id) in self._carts:
            cart = self._carts.pop(str(cart_id))
            if cart.user_id and str(cart.user_id) in self._carts_by_user:
                del self._carts_by_user[str(cart.user_id)]


class TestRemoveFromCartUseCase:
    """RemoveFromCartUseCaseの単体テスト."""

    def test_アイテムを削除できる(self) -> None:
        """アイテムを削除できることを確認."""
        from src.application.use_cases.remove_from_cart import RemoveFromCartUseCase

        repository = MockCartRepository()
        cart = Cart.create()
        item = cart.add_item(
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        repository.save(cart)

        use_case = RemoveFromCartUseCase(repository)
        result = use_case.execute(cart.cart_id, item.item_id)

        assert result.success is True
        assert result.item_count == 0
        assert result.total_amount.value == 0

    def test_存在しないカートIDでエラー(self) -> None:
        """存在しないカートIDでエラーが発生することを確認."""
        from src.application.use_cases.remove_from_cart import (
            CartNotFoundError,
            RemoveFromCartUseCase,
        )

        repository = MockCartRepository()
        use_case = RemoveFromCartUseCase(repository)

        with pytest.raises(CartNotFoundError):
            use_case.execute(CartId("nonexistent"), ItemId("item1"))

    def test_存在しないアイテムIDでエラー(self) -> None:
        """存在しないアイテムIDでエラーが発生することを確認."""
        from src.application.use_cases.remove_from_cart import (
            ItemNotFoundError,
            RemoveFromCartUseCase,
        )

        repository = MockCartRepository()
        cart = Cart.create()
        repository.save(cart)

        use_case = RemoveFromCartUseCase(repository)

        with pytest.raises(ItemNotFoundError):
            use_case.execute(cart.cart_id, ItemId("nonexistent"))

    def test_複数アイテムから一つを削除できる(self) -> None:
        """複数アイテムから一つを削除できることを確認."""
        from src.application.use_cases.remove_from_cart import RemoveFromCartUseCase

        repository = MockCartRepository()
        cart = Cart.create()
        item1 = cart.add_item(
            race_id=RaceId("2024060101"),
            race_name="1R",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        cart.add_item(
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=BetSelection(
                bet_type=BetType.QUINELLA,
                horse_numbers=HorseNumbers([1, 2]),
                amount=Money(500),
            ),
        )
        repository.save(cart)

        use_case = RemoveFromCartUseCase(repository)
        result = use_case.execute(cart.cart_id, item1.item_id)

        assert result.success is True
        assert result.item_count == 1
        assert result.total_amount.value == 500
