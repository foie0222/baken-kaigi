"""券種の列挙型."""
from enum import Enum


class BetType(Enum):
    """馬券の券種."""

    WIN = "win"  # 単勝
    PLACE = "place"  # 複勝
    QUINELLA = "quinella"  # 馬連
    QUINELLA_PLACE = "quinella_place"  # ワイド
    EXACTA = "exacta"  # 馬単
    TRIO = "trio"  # 三連複
    TRIFECTA = "trifecta"  # 三連単

    def get_required_count(self) -> int:
        """必要な選択頭数を返す."""
        counts = {
            BetType.WIN: 1,
            BetType.PLACE: 1,
            BetType.QUINELLA: 2,
            BetType.QUINELLA_PLACE: 2,
            BetType.EXACTA: 2,
            BetType.TRIO: 3,
            BetType.TRIFECTA: 3,
        }
        return counts[self]

    def get_display_name(self) -> str:
        """日本語表示名を返す."""
        names = {
            BetType.WIN: "単勝",
            BetType.PLACE: "複勝",
            BetType.QUINELLA: "馬連",
            BetType.QUINELLA_PLACE: "ワイド",
            BetType.EXACTA: "馬単",
            BetType.TRIO: "三連複",
            BetType.TRIFECTA: "三連単",
        }
        return names[self]

    def is_order_required(self) -> bool:
        """順序が必要か（馬単、三連単）."""
        return self in (BetType.EXACTA, BetType.TRIFECTA)
