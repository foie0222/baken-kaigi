"""好み設定値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import BetTypePreference


@dataclass(frozen=True)
class BettingPreference:
    """ユーザーの馬券購入好み設定."""

    bet_type_preference: BetTypePreference
    min_probability: float = 0.0
    min_ev: float = 0.0
    max_probability: float | None = None
    max_ev: float | None = None
    race_budget: int = 0  # 1レースあたりの予算（円）

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
            "min_ev": self.min_ev,
            "max_probability": self.max_probability,
            "max_ev": self.max_ev,
            "race_budget": self.race_budget,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> BettingPreference:
        """辞書から復元する."""
        if not data:
            return cls.default()
        max_prob_raw = data.get("max_probability")
        max_ev_raw = data.get("max_ev")
        return cls(
            bet_type_preference=BetTypePreference(data.get("bet_type_preference", "auto")),
            min_probability=float(data.get("min_probability", 0.0)),
            min_ev=float(data.get("min_ev", 0.0)),
            max_probability=float(max_prob_raw) if max_prob_raw is not None else None,
            max_ev=float(max_ev_raw) if max_ev_raw is not None else None,
            race_budget=int(data.get("race_budget", 0)),
        )
