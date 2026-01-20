"""AddToCartUseCaseのテスト."""
from datetime import datetime

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


class TestAddToCartUseCase:
    """AddToCartUseCaseの単体テスト."""

    def test_新規カートに買い目を追加できる(self) -> None:
        """新規カートに買い目を追加できることを確認."""
        from src.application.use_cases.add_to_cart import AddToCartUseCase

        repository = MockCartRepository()
        use_case = AddToCartUseCase(repository)
        bet = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers([1]),
            amount=Money(100),
        )

        result = use_case.execute(
            cart_id=None,
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=bet,
        )

        assert result.cart_id is not None
        assert result.item_count == 1
        assert result.total_amount.value == 100

    def test_既存カートに買い目を追加できる(self) -> None:
        """既存カートに買い目を追加できることを確認."""
        from src.application.use_cases.add_to_cart import AddToCartUseCase

        repository = MockCartRepository()
        existing_cart = Cart.create()
        existing_cart.add_item(
            race_id=RaceId("2024060101"),
            race_name="1R",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        repository.save(existing_cart)

        use_case = AddToCartUseCase(repository)
        bet = BetSelection(
            bet_type=BetType.QUINELLA,
            horse_numbers=HorseNumbers([1, 2]),
            amount=Money(500),
        )

        result = use_case.execute(
            cart_id=existing_cart.cart_id,
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=bet,
        )

        assert result.cart_id == existing_cart.cart_id
        assert result.item_count == 2
        assert result.total_amount.value == 600

    def test_存在しないカートIDでエラー(self) -> None:
        """存在しないカートIDでエラーが発生することを確認."""
        from src.application.use_cases.add_to_cart import (
            AddToCartUseCase,
            CartNotFoundError,
        )

        repository = MockCartRepository()
        use_case = AddToCartUseCase(repository)
        bet = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers([1]),
            amount=Money(100),
        )

        with pytest.raises(CartNotFoundError):
            use_case.execute(
                cart_id=CartId("nonexistent"),
                race_id=RaceId("2024060111"),
                race_name="日本ダービー",
                bet_selection=bet,
            )

    def test_異なるレースの買い目も同じカートに追加できる(self) -> None:
        """異なるレースの買い目も同じカートに追加できることを確認."""
        from src.application.use_cases.add_to_cart import AddToCartUseCase

        repository = MockCartRepository()
        use_case = AddToCartUseCase(repository)

        # 1つ目のレース
        bet1 = BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers([1]),
            amount=Money(100),
        )
        result1 = use_case.execute(
            cart_id=None,
            race_id=RaceId("2024060101"),
            race_name="1R",
            bet_selection=bet1,
        )

        # 2つ目のレース
        bet2 = BetSelection(
            bet_type=BetType.TRIFECTA,
            horse_numbers=HorseNumbers([1, 2, 3]),
            amount=Money(200),
        )
        result2 = use_case.execute(
            cart_id=result1.cart_id,
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=bet2,
        )

        assert result2.item_count == 2
        assert result2.total_amount.value == 300
