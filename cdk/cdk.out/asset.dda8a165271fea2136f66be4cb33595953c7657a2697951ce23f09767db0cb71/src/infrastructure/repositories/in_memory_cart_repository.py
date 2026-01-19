"""カートリポジトリのインメモリ実装."""
from src.domain.entities import Cart
from src.domain.identifiers import CartId, UserId
from src.domain.ports import CartRepository


class InMemoryCartRepository(CartRepository):
    """カートリポジトリのインメモリ実装."""

    def __init__(self) -> None:
        """初期化."""
        self._carts: dict[str, Cart] = {}

    def save(self, cart: Cart) -> None:
        """カートを保存する."""
        self._carts[cart.cart_id.value] = cart

    def find_by_id(self, cart_id: CartId) -> Cart | None:
        """カートIDで検索する."""
        return self._carts.get(cart_id.value)

    def find_by_user_id(self, user_id: UserId) -> Cart | None:
        """ユーザーIDで検索する."""
        for cart in self._carts.values():
            if cart.user_id is not None and cart.user_id == user_id:
                return cart
        return None

    def delete(self, cart_id: CartId) -> None:
        """カートを削除する."""
        self._carts.pop(cart_id.value, None)
