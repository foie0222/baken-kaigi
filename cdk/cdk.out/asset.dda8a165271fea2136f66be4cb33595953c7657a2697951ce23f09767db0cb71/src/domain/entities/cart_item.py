"""カート内アイテムエンティティ."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..enums import BetType
from ..identifiers import ItemId, RaceId
from ..value_objects import BetSelection, HorseNumbers, Money


@dataclass(frozen=True)
class CartItem:
    """カートに追加された個々の買い目（Cart集約内でのみ意味を持つ）."""

    item_id: ItemId
    race_id: RaceId
    race_name: str  # 表示用キャッシュ
    bet_selection: BetSelection
    added_at: datetime

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.race_name:
            raise ValueError("Race name cannot be empty")

    @classmethod
    def create(
        cls,
        race_id: RaceId,
        race_name: str,
        bet_selection: BetSelection,
        added_at: datetime | None = None,
    ) -> CartItem:
        """新しいカートアイテムを作成する."""
        return cls(
            item_id=ItemId.generate(),
            race_id=race_id,
            race_name=race_name,
            bet_selection=bet_selection,
            added_at=added_at or datetime.now(),
        )

    def get_amount(self) -> Money:
        """買い目の金額を取得."""
        return self.bet_selection.amount

    def get_bet_type(self) -> BetType:
        """券種を取得."""
        return self.bet_selection.bet_type

    def get_selected_numbers(self) -> HorseNumbers:
        """選択馬番を取得."""
        return self.bet_selection.horse_numbers
