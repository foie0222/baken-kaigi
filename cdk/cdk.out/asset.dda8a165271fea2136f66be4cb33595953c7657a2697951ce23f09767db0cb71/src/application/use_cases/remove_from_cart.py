"""カートアイテム削除ユースケース."""
from dataclasses import dataclass

from src.domain.identifiers import CartId, ItemId
from src.domain.ports import CartRepository
from src.domain.value_objects import Money


class CartNotFoundError(Exception):
    """カートが見つからないエラー."""

    def __init__(self, cart_id: CartId) -> None:
        self.cart_id = cart_id
        super().__init__(f"Cart not found: {cart_id}")


class ItemNotFoundError(Exception):
    """アイテムが見つからないエラー."""

    def __init__(self, item_id: ItemId) -> None:
        self.item_id = item_id
        super().__init__(f"Item not found: {item_id}")


@dataclass(frozen=True)
class RemoveFromCartResult:
    """カートアイテム削除結果."""

    success: bool
    item_count: int
    total_amount: Money


class RemoveFromCartUseCase:
    """カートからアイテムを削除するユースケース."""

    def __init__(self, cart_repository: CartRepository) -> None:
        """初期化.

        Args:
            cart_repository: カートリポジトリ
        """
        self._cart_repository = cart_repository

    def execute(self, cart_id: CartId, item_id: ItemId) -> RemoveFromCartResult:
        """アイテムをカートから削除する.

        Args:
            cart_id: カートID
            item_id: アイテムID

        Returns:
            削除結果

        Raises:
            CartNotFoundError: カートが見つからない場合
            ItemNotFoundError: アイテムが見つからない場合
        """
        cart = self._cart_repository.find_by_id(cart_id)
        if cart is None:
            raise CartNotFoundError(cart_id)

        success = cart.remove_item(item_id)
        if not success:
            raise ItemNotFoundError(item_id)

        self._cart_repository.save(cart)

        return RemoveFromCartResult(
            success=True,
            item_count=cart.get_item_count(),
            total_amount=cart.get_total_amount(),
        )
