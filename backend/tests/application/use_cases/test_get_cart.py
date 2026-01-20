"""GetCartUseCaseのテスト."""
import pytest

from src.domain.entities import Cart
from src.domain.enums import BetType
from src.domain.identifiers import CartId, RaceId, UserId
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


class TestGetCartUseCase:
    """GetCartUseCaseの単体テスト."""

    def test_カートIDでカートを取得できる(self) -> None:
        """カートIDでカートを取得できることを確認."""
        from src.application.use_cases.get_cart import GetCartUseCase

        repository = MockCartRepository()
        cart = Cart.create()
        cart.add_item(
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        repository.save(cart)

        use_case = GetCartUseCase(repository)
        result = use_case.execute(cart.cart_id)

        assert result is not None
        assert result.cart_id == cart.cart_id
        assert len(result.items) == 1
        assert result.total_amount.value == 100

    def test_存在しないカートIDでNoneを返す(self) -> None:
        """存在しないカートIDでNoneが返ることを確認."""
        from src.application.use_cases.get_cart import GetCartUseCase

        repository = MockCartRepository()
        use_case = GetCartUseCase(repository)

        result = use_case.execute(CartId("nonexistent"))

        assert result is None

    def test_空のカートを取得できる(self) -> None:
        """空のカートを取得できることを確認."""
        from src.application.use_cases.get_cart import GetCartUseCase

        repository = MockCartRepository()
        cart = Cart.create()
        repository.save(cart)

        use_case = GetCartUseCase(repository)
        result = use_case.execute(cart.cart_id)

        assert result is not None
        assert result.items == []
        assert result.total_amount.value == 0
        assert result.is_empty is True

    def test_複数アイテムのカートを取得できる(self) -> None:
        """複数アイテムのカートを取得できることを確認."""
        from src.application.use_cases.get_cart import GetCartUseCase

        repository = MockCartRepository()
        cart = Cart.create()
        cart.add_item(
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

        use_case = GetCartUseCase(repository)
        result = use_case.execute(cart.cart_id)

        assert result is not None
        assert len(result.items) == 2
        assert result.total_amount.value == 600
        assert result.is_empty is False
