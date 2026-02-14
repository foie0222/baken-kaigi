"""リポジトリのテスト."""
from abc import ABC

import pytest

from src.domain.value_objects import BetSelection
from src.domain.enums import BetType
from src.domain.entities import Cart
from src.domain.entities import CartItem
from src.domain.ports import CartRepository
from src.domain.value_objects import HorseNumbers
from src.infrastructure.repositories import InMemoryCartRepository
from src.domain.value_objects import Money
from src.domain.identifiers import RaceId


class TestCartRepository:
    """CartRepositoryの単体テスト."""

    def test_CartRepositoryは抽象基底クラスである(self) -> None:
        """CartRepositoryがABCを継承していることを確認."""
        assert issubclass(CartRepository, ABC)


class TestInMemoryCartRepository:
    """InMemoryCartRepositoryの単体テスト."""

    def test_saveで保存しfind_by_idで取得できる(self) -> None:
        """saveで保存したカートをfind_by_idで取得できることを確認."""
        repo = InMemoryCartRepository()
        cart = Cart.create()
        repo.save(cart)
        found = repo.find_by_id(cart.cart_id)
        assert found is not None
        assert found.cart_id == cart.cart_id

    def test_find_by_idで存在しないIDはNone(self) -> None:
        """find_by_idで存在しないIDを指定するとNoneが返ることを確認."""
        repo = InMemoryCartRepository()
        from src.domain.identifiers import CartId
        assert repo.find_by_id(CartId("nonexistent")) is None

    def test_saveで既存カートを更新できる(self) -> None:
        """saveで既存のカートを更新できることを確認."""
        repo = InMemoryCartRepository()
        cart = Cart.create()
        repo.save(cart)
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        cart.add_item(RaceId("r1"), "レース1", bet)
        repo.save(cart)
        found = repo.find_by_id(cart.cart_id)
        assert found.get_item_count() == 1

    def test_deleteで削除できる(self) -> None:
        """deleteでカートを削除できることを確認."""
        repo = InMemoryCartRepository()
        cart = Cart.create()
        repo.save(cart)
        repo.delete(cart.cart_id)
        assert repo.find_by_id(cart.cart_id) is None

    def test_deleteで存在しないIDは何もしない(self) -> None:
        """deleteで存在しないIDを指定しても例外が発生しないことを確認."""
        repo = InMemoryCartRepository()
        from src.domain.identifiers import CartId
        repo.delete(CartId("nonexistent"))  # 例外が発生しない

    def test_find_by_user_idでユーザーのカートを取得(self) -> None:
        """find_by_user_idでユーザーに紐付いたカートを取得できることを確認."""
        repo = InMemoryCartRepository()
        from src.domain.identifiers import UserId
        cart = Cart.create(user_id=UserId("user-1"))
        repo.save(cart)
        found = repo.find_by_user_id(UserId("user-1"))
        assert found is not None
        assert found.user_id.value == "user-1"

    def test_find_by_user_idで存在しないユーザーはNone(self) -> None:
        """find_by_user_idで存在しないユーザーを指定するとNoneが返ることを確認."""
        repo = InMemoryCartRepository()
        from src.domain.identifiers import UserId
        assert repo.find_by_user_id(UserId("nonexistent")) is None
