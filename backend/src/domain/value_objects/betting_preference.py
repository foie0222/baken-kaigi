"""好み設定値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import BetTypePreference, BettingPriority, TargetStyle


@dataclass(frozen=True)
class BettingPreference:
    """ユーザーの馬券購入好み設定."""

    bet_type_preference: BetTypePreference
    target_style: TargetStyle
    priority: BettingPriority

    @classmethod
    def default(cls) -> BettingPreference:
        """デフォルト値で作成する."""
        return cls(
            bet_type_preference=BetTypePreference.AUTO,
            target_style=TargetStyle.MEDIUM_LONGSHOT,
            priority=BettingPriority.BALANCED,
        )

    def to_dict(self) -> dict:
        """辞書に変換する."""
        return {
            "bet_type_preference": self.bet_type_preference.value,
            "target_style": self.target_style.value,
            "priority": self.priority.value,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> BettingPreference:
        """辞書から復元する."""
        if not data:
            return cls.default()
        return cls(
            bet_type_preference=BetTypePreference(data.get("bet_type_preference", "auto")),
            target_style=TargetStyle(data.get("target_style", "medium_longshot")),
            priority=BettingPriority(data.get("priority", "balanced")),
        )
