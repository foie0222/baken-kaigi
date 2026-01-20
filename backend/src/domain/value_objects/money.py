"""金額を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    """金額（円）を表現する値オブジェクト."""

    value: int

    def __post_init__(self) -> None:
        """バリデーション."""
        if self.value < 0:
            raise ValueError("Money value cannot be negative")

    @classmethod
    def of(cls, value: int) -> Money:
        """指定金額でMoneyを生成する."""
        return cls(value)

    @classmethod
    def zero(cls) -> Money:
        """ゼロ円を生成する."""
        return cls(0)

    @classmethod
    def from_preset(cls, preset: int) -> Money:
        """プリセット値から生成する（100, 500, 1000, 5000）."""
        valid_presets = (100, 500, 1000, 5000)
        if preset not in valid_presets:
            raise ValueError(f"Invalid preset: {preset}. Valid presets are {valid_presets}")
        return cls(preset)

    def add(self, other: Money) -> Money:
        """金額を加算して新しいMoneyを返す."""
        return Money(self.value + other.value)

    def subtract(self, other: Money) -> Money:
        """金額を減算して新しいMoneyを返す."""
        result = self.value - other.value
        if result < 0:
            raise ValueError("Subtraction would result in negative value")
        return Money(result)

    def multiply(self, factor: int) -> Money:
        """金額を乗算して新しいMoneyを返す."""
        if factor < 0:
            raise ValueError("Factor cannot be negative")
        return Money(self.value * factor)

    def is_greater_than(self, other: Money) -> bool:
        """この金額が他の金額より大きいか判定."""
        return self.value > other.value

    def is_less_than_or_equal(self, other: Money) -> bool:
        """この金額が他の金額以下か判定."""
        return self.value <= other.value

    def is_valid_bet_amount(self) -> bool:
        """有効な掛け金額か判定（100円以上、100円単位）."""
        return self.value >= 100 and self.value % 100 == 0

    def format(self) -> str:
        """表示用フォーマット（例: "¥1,000"）."""
        return f"¥{self.value:,}"

    def __str__(self) -> str:
        """文字列表現."""
        return self.format()
