"""カートリポジトリインターフェース."""
from abc import ABC, abstractmethod

from ..entities import Cart
from ..identifiers import CartId, UserId


class CartRepository(ABC):
    """カートリポジトリのインターフェース."""

    @abstractmethod
    def save(self, cart: Cart) -> None:
        """カートを保存する."""
        pass

    @abstractmethod
    def find_by_id(self, cart_id: CartId) -> Cart | None:
        """カートIDで検索する."""
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: UserId) -> Cart | None:
        """ユーザーIDで検索する."""
        pass

    @abstractmethod
    def delete(self, cart_id: CartId) -> None:
        """カートを削除する."""
        pass
