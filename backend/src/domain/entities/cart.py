"""カート集約ルート."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..identifiers import CartId, ItemId, RaceId, UserId
from ..value_objects import BetSelection, Money

from .cart_item import CartItem


@dataclass
class Cart:
    """ユーザーが購入を検討する複数の買い目を一時的に保持するコンテナ（集約ルート）."""

    cart_id: CartId
    user_id: UserId | None = None
    _items: list[CartItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(cls, user_id: UserId | None = None) -> Cart:
        """新しいカートを作成する."""
        now = datetime.now(timezone.utc)
        return cls(
            cart_id=CartId.generate(),
            user_id=user_id,
            _items=[],
            created_at=now,
            updated_at=now,
        )

    def add_item(
        self, race_id: RaceId, race_name: str, bet_selection: BetSelection
    ) -> CartItem:
        """買い目をカートに追加する."""
        item = CartItem.create(
            race_id=race_id,
            race_name=race_name,
            bet_selection=bet_selection,
        )
        self._items.append(item)
        self.updated_at = datetime.now(timezone.utc)
        return item

    def remove_item(self, item_id: ItemId) -> bool:
        """指定アイテムを削除する."""
        for i, item in enumerate(self._items):
            if item.item_id == item_id:
                self._items.pop(i)
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False

    def clear(self) -> None:
        """全アイテムを削除する."""
        self._items.clear()
        self.updated_at = datetime.now(timezone.utc)

    def get_total_amount(self) -> Money:
        """合計金額を計算する."""
        total = Money.zero()
        for item in self._items:
            total = total.add(item.get_amount())
        return total

    def get_item_count(self) -> int:
        """アイテム数を取得する."""
        return len(self._items)

    def is_empty(self) -> bool:
        """カートが空か判定する."""
        return len(self._items) == 0

    def get_items(self) -> list[CartItem]:
        """アイテムのリストを取得（防御的コピー）."""
        return list(self._items)

    def get_item(self, item_id: ItemId) -> CartItem | None:
        """指定IDのアイテムを取得する."""
        for item in self._items:
            if item.item_id == item_id:
                return item
        return None

    def associate_user(self, user_id: UserId) -> None:
        """ユーザーを紐付ける."""
        if self.user_id is not None:
            raise ValueError("User is already associated with this cart")
        self.user_id = user_id
        self.updated_at = datetime.now(timezone.utc)
