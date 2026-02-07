"""IPAT競馬場コードの列挙型."""
from __future__ import annotations

from enum import Enum


class IpatVenueCode(Enum):
    """IPAT投票用の競馬場コード."""

    SAPPORO = "01"
    HAKODATE = "02"
    FUKUSHIMA = "03"
    NIIGATA = "04"
    TOKYO = "05"
    NAKAYAMA = "06"
    CHUKYO = "07"
    KYOTO = "08"
    HANSHIN = "09"
    KOKURA = "10"

    @classmethod
    def from_course_code(cls, code: str) -> IpatVenueCode:
        """2桁コースコードからIpatVenueCodeに変換する."""
        for venue in cls:
            if venue.value == code:
                return venue
        raise ValueError(f"Unknown course code: {code}")
