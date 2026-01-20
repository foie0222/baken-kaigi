"""買い目を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import BetType

from .horse_numbers import HorseNumbers
from .money import Money


@dataclass(frozen=True)
class BetSelection:
    """ユーザーが入力した馬券の買い目."""

    bet_type: BetType
    horse_numbers: HorseNumbers
    amount: Money

    def __post_init__(self) -> None:
        """バリデーション."""
        errors = self._validate()
        if errors:
            raise ValueError(f"Invalid BetSelection: {', '.join(errors)}")

    def _validate(self) -> list[str]:
        """バリデーションを実行し、エラーメッセージのリストを返す."""
        errors = []

        required = self.bet_type.get_required_count()
        actual = self.horse_numbers.count()
        if actual != required:
            errors.append(
                f"{self.bet_type.get_display_name()} requires {required} horses, got {actual}"
            )

        if not self.amount.is_valid_bet_amount():
            errors.append("Amount must be at least 100 yen and in 100 yen increments")

        return errors

    @classmethod
    def create(
        cls, bet_type: BetType, horse_numbers: HorseNumbers, amount: Money
    ) -> BetSelection:
        """バリデーション付きで生成する."""
        return cls(bet_type, horse_numbers, amount)

    def is_valid(self) -> bool:
        """買い目が有効か検証."""
        return len(self._validate()) == 0

    def get_required_count(self) -> int:
        """券種に必要な選択頭数を取得."""
        return self.bet_type.get_required_count()

    def get_amount(self) -> Money:
        """金額を取得."""
        return self.amount

    def get_bet_type(self) -> BetType:
        """券種を取得."""
        return self.bet_type
