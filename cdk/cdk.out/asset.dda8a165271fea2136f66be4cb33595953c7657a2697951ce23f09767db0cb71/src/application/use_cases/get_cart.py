"""カート取得ユースケース."""
from dataclasses import dataclass

from src.domain.entities import CartItem
from src.domain.identifiers import CartId
from src.domain.ports import CartRepository
from src.domain.value_objects import Money


@dataclass(frozen=True)
class CartItemDTO:
    """カートアイテムDTO."""

    item_id: str
    race_id: str
    race_name: str
    bet_type: str
    horse_numbers: list[int]
    amount: Money


@dataclass(frozen=True)
class GetCartResult:
    """カート取得結果."""

    cart_id: CartId
    items: list[CartItemDTO]
    total_amount: Money
    is_empty: bool


class GetCartUseCase:
    """カート取得ユースケース."""

    def __init__(self, cart_repository: CartRepository) -> None:
        """初期化.

        Args:
            cart_repository: カートリポジトリ
        """
        self._cart_repository = cart_repository

    def execute(self, cart_id: CartId) -> GetCartResult | None:
        """カートを取得する.

        Args:
            cart_id: カートID

        Returns:
            カート取得結果（存在しない場合はNone）
        """
        cart = self._cart_repository.find_by_id(cart_id)
        if cart is None:
            return None

        items = [
            CartItemDTO(
                item_id=str(item.item_id),
                race_id=str(item.race_id),
                race_name=item.race_name,
                bet_type=item.bet_selection.bet_type.value,
                horse_numbers=item.bet_selection.horse_numbers.to_list(),
                amount=item.get_amount(),
            )
            for item in cart.get_items()
        ]

        return GetCartResult(
            cart_id=cart.cart_id,
            items=items,
            total_amount=cart.get_total_amount(),
            is_empty=cart.is_empty(),
        )
