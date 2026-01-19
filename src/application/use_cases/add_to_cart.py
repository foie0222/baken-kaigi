"""カート追加ユースケース."""
from dataclasses import dataclass

from src.domain.entities import Cart
from src.domain.identifiers import CartId, ItemId, RaceId
from src.domain.ports import CartRepository
from src.domain.value_objects import BetSelection, Money


class CartNotFoundError(Exception):
    """カートが見つからないエラー."""

    def __init__(self, cart_id: CartId) -> None:
        self.cart_id = cart_id
        super().__init__(f"Cart not found: {cart_id}")


@dataclass(frozen=True)
class AddToCartResult:
    """カート追加結果."""

    cart_id: CartId
    item_id: ItemId
    item_count: int
    total_amount: Money


class AddToCartUseCase:
    """カートに買い目を追加するユースケース."""

    def __init__(self, cart_repository: CartRepository) -> None:
        """初期化.

        Args:
            cart_repository: カートリポジトリ
        """
        self._cart_repository = cart_repository

    def execute(
        self,
        cart_id: CartId | None,
        race_id: RaceId,
        race_name: str,
        bet_selection: BetSelection,
    ) -> AddToCartResult:
        """買い目をカートに追加する.

        Args:
            cart_id: カートID（新規の場合はNone）
            race_id: レースID
            race_name: レース名
            bet_selection: 買い目

        Returns:
            カート追加結果

        Raises:
            CartNotFoundError: 指定されたカートが存在しない場合
        """
        if cart_id is None:
            cart = Cart.create()
        else:
            cart = self._cart_repository.find_by_id(cart_id)
            if cart is None:
                raise CartNotFoundError(cart_id)

        item = cart.add_item(
            race_id=race_id,
            race_name=race_name,
            bet_selection=bet_selection,
        )

        self._cart_repository.save(cart)

        return AddToCartResult(
            cart_id=cart.cart_id,
            item_id=item.item_id,
            item_count=cart.get_item_count(),
            total_amount=cart.get_total_amount(),
        )
