"""カートクリアユースケース."""
from dataclasses import dataclass

from src.domain.identifiers import CartId
from src.domain.ports import CartRepository
from src.domain.value_objects import Money


class CartNotFoundError(Exception):
    """カートが見つからないエラー."""

    def __init__(self, cart_id: CartId) -> None:
        self.cart_id = cart_id
        super().__init__(f"Cart not found: {cart_id}")


@dataclass(frozen=True)
class ClearCartResult:
    """カートクリア結果."""

    success: bool
    item_count: int
    total_amount: Money


class ClearCartUseCase:
    """カートを全クリアするユースケース."""

    def __init__(self, cart_repository: CartRepository) -> None:
        """初期化.

        Args:
            cart_repository: カートリポジトリ
        """
        self._cart_repository = cart_repository

    def execute(self, cart_id: CartId) -> ClearCartResult:
        """カートを全クリアする.

        Args:
            cart_id: カートID

        Returns:
            クリア結果

        Raises:
            CartNotFoundError: カートが見つからない場合
        """
        cart = self._cart_repository.find_by_id(cart_id)
        if cart is None:
            raise CartNotFoundError(cart_id)

        cart.clear()
        self._cart_repository.save(cart)

        return ClearCartResult(
            success=True,
            item_count=cart.get_item_count(),
            total_amount=cart.get_total_amount(),
        )
