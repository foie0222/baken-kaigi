"""BetProposal → IpatBetLine 直接変換.

Cart を経由せず、買い目提案から直接 IPAT投票行を生成する。
"""
from ..enums import IpatBetType, IpatVenueCode
from ..value_objects import IpatBetLine
from .bet_generator import BetProposal

_BET_TYPE_MAP = {
    "win": IpatBetType.TANSYO,
    "place": IpatBetType.FUKUSYO,
    "wide": IpatBetType.WIDE,
    "quinella": IpatBetType.UMAREN,
    "exacta": IpatBetType.UMATAN,
}


class BetToIpatConverter:
    """BetProposal を IpatBetLine に変換."""

    @staticmethod
    def convert(race_id: str, proposals: list[BetProposal]) -> list[IpatBetLine]:
        """race_id と買い目リストから IpatBetLine リストを生成."""
        opdt = race_id[:8]
        venue_code = IpatVenueCode.from_course_code(race_id[8:10])
        race_number = int(race_id[10:12])

        lines = []
        for p in proposals:
            ipat_type = _BET_TYPE_MAP[p.bet_type]
            number = "-".join(f"{n:02d}" for n in p.horse_numbers)
            lines.append(
                IpatBetLine(
                    opdt=opdt,
                    venue_code=venue_code,
                    race_number=race_number,
                    bet_type=ipat_type,
                    number=number,
                    amount=p.amount,
                )
            )
        return lines
