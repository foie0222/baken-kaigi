"""生年月日を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DateOfBirth:
    """生年月日の値オブジェクト."""

    value: date

    _MINIMUM_AGE = 20

    def __post_init__(self) -> None:
        """バリデーション."""
        if not isinstance(self.value, date):
            raise TypeError("DateOfBirth must be a date instance")
        if self.value > date.today():
            raise ValueError("DateOfBirth cannot be in the future")
        if self.age() < self._MINIMUM_AGE:
            raise ValueError(f"Must be at least {self._MINIMUM_AGE} years old")

    def age(self) -> int:
        """現在の年齢を計算する."""
        today = date.today()
        age = today.year - self.value.year
        if (today.month, today.day) < (self.value.month, self.value.day):
            age -= 1
        return age

    def __str__(self) -> str:
        """文字列表現."""
        return self.value.isoformat()
