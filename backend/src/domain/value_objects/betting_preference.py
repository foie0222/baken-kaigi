"""好み設定値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import BetTypePreference


@dataclass(frozen=True)
class BettingPreference:
    """ユーザーの馬券購入好み設定."""

    bet_type_preference: BetTypePreference
    min_probability: float = 0.01
    max_probability: float = 0.50
    min_ev: float = 1.0
    max_ev: float = 10.0

    @classmethod
    def default(cls) -> BettingPreference:
        """デフォルト値で作成する."""
        return cls(
            bet_type_preference=BetTypePreference.AUTO,
        )

    def to_dict(self) -> dict:
        """辞書に変換する."""
        return {
            "bet_type_preference": self.bet_type_preference.value,
            "min_probability": self.min_probability,
            "max_probability": self.max_probability,
            "min_ev": self.min_ev,
            "max_ev": self.max_ev,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> BettingPreference:
        """辞書から復元する."""
        if not data:
            return cls.default()
        return cls(
            bet_type_preference=BetTypePreference(data.get("bet_type_preference", "auto")),
            min_probability=float(data.get("min_probability", 0.01)),
            max_probability=float(data.get("max_probability", 0.50)),
            min_ev=float(data.get("min_ev", 1.0)),
            max_ev=float(data.get("max_ev", 10.0)),
        )
