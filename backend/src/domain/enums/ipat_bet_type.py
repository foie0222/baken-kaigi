"""IPAT券種の列挙型."""
from __future__ import annotations

from enum import Enum

from .bet_type import BetType


class IpatBetType(Enum):
    """IPAT投票用の券種."""

    TANSYO = "tansyo"
    FUKUSYO = "fukusyo"
    UMAREN = "umaren"
    WIDE = "wide"
    UMATAN = "umatan"
    SANRENPUKU = "sanrenpuku"
    SANRENTAN = "sanrentan"

    @classmethod
    def from_bet_type(cls, bet_type: BetType) -> IpatBetType:
        """BetTypeからIpatBetTypeに変換する."""
        mapping = {
            BetType.WIN: cls.TANSYO,
            BetType.PLACE: cls.FUKUSYO,
            BetType.QUINELLA: cls.UMAREN,
            BetType.QUINELLA_PLACE: cls.WIDE,
            BetType.EXACTA: cls.UMATAN,
            BetType.TRIO: cls.SANRENPUKU,
            BetType.TRIFECTA: cls.SANRENTAN,
        }
        return mapping[bet_type]
