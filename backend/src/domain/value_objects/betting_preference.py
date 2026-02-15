"""好み設定値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import BetTypePreference


@dataclass(frozen=True)
class BettingPreference:
    """ユーザーの馬券購入好み設定."""

    bet_type_preference: BetTypePreference

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
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> BettingPreference:
        """辞書から復元する."""
        if not data:
            return cls.default()
        return cls(
            bet_type_preference=BetTypePreference(data.get("bet_type_preference", "auto")),
        )
