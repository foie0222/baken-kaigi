"""選択馬番のコレクションを表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HorseNumbers:
    """選択された馬番のコレクション."""

    numbers: tuple[int, ...]

    def __post_init__(self) -> None:
        """バリデーション."""
        for num in self.numbers:
            if not 1 <= num <= 18:
                raise ValueError(f"Horse number must be between 1 and 18, got {num}")

        if len(self.numbers) != len(set(self.numbers)):
            raise ValueError("Horse numbers must not contain duplicates")

    @classmethod
    def of(cls, *numbers: int) -> HorseNumbers:
        """可変長引数で生成する."""
        return cls(tuple(numbers))

    @classmethod
    def from_list(cls, numbers: list[int]) -> HorseNumbers:
        """リストから生成する."""
        return cls(tuple(numbers))

    def count(self) -> int:
        """選択された馬番の数を返す."""
        return len(self.numbers)

    def contains(self, number: int) -> bool:
        """指定馬番が含まれるか判定."""
        return number in self.numbers

    def to_list(self) -> list[int]:
        """リストとして取得."""
        return list(self.numbers)

    def to_display_string(self) -> str:
        """表示用文字列（例: "3-5-8"）."""
        return "-".join(str(n) for n in self.numbers)

    def __str__(self) -> str:
        """文字列表現."""
        return self.to_display_string()
