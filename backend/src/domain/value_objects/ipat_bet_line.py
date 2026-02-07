"""IPAT投票行を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import IpatBetType, IpatVenueCode


@dataclass(frozen=True)
class IpatBetLine:
    """IPAT投票の1行分のデータ."""

    opdt: str
    venue_code: IpatVenueCode
    race_number: int
    bet_type: IpatBetType
    number: str
    amount: int

    def __post_init__(self) -> None:
        """バリデーション."""
        if not 1 <= self.race_number <= 12:
            raise ValueError("レース番号は1から12の範囲である必要があります")
        if self.amount < 100 or self.amount % 100 != 0:
            raise ValueError("金額は100円単位である必要があります")

    def to_csv_line(self) -> str:
        """CSV行に変換する."""
        rno = f"{self.race_number:02d}"
        return f"{self.opdt},{self.venue_code.value},{rno},{self.bet_type.value},NORMAL,,{self.number},{self.amount}"
