"""エージェント能力値の値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


MIN_STAT = 0
MAX_STAT = 100


@dataclass(frozen=True)
class AgentStats:
    """エージェントの能力パラメータ（各0〜100）."""

    data_analysis: int  # データ分析力
    pace_reading: int  # 展開読み力
    risk_management: int  # リスク管理力
    intuition: int  # 直感力

    def __post_init__(self) -> None:
        """バリデーション."""
        for name, val in [
            ("data_analysis", self.data_analysis),
            ("pace_reading", self.pace_reading),
            ("risk_management", self.risk_management),
            ("intuition", self.intuition),
        ]:
            if not isinstance(val, int):
                raise TypeError(f"{name} must be int, got {type(val).__name__}")
            if val < MIN_STAT or val > MAX_STAT:
                raise ValueError(
                    f"{name} must be between {MIN_STAT} and {MAX_STAT}, got {val}"
                )

    @classmethod
    def initial_for_style(cls, style: str) -> AgentStats:
        """スタイルに応じた初期能力値を生成する."""
        defaults = {
            "solid": cls(data_analysis=40, pace_reading=30, risk_management=50, intuition=20),
            "longshot": cls(data_analysis=20, pace_reading=30, risk_management=20, intuition=50),
            "data": cls(data_analysis=60, pace_reading=20, risk_management=30, intuition=10),
            "pace": cls(data_analysis=20, pace_reading=60, risk_management=20, intuition=30),
        }
        if style not in defaults:
            raise ValueError(f"Unknown style: {style}")
        return defaults[style]

    def apply_change(
        self,
        data_analysis: int = 0,
        pace_reading: int = 0,
        risk_management: int = 0,
        intuition: int = 0,
    ) -> AgentStats:
        """能力値を変更した新しいAgentStatsを返す."""
        return AgentStats(
            data_analysis=max(MIN_STAT, min(MAX_STAT, self.data_analysis + data_analysis)),
            pace_reading=max(MIN_STAT, min(MAX_STAT, self.pace_reading + pace_reading)),
            risk_management=max(MIN_STAT, min(MAX_STAT, self.risk_management + risk_management)),
            intuition=max(MIN_STAT, min(MAX_STAT, self.intuition + intuition)),
        )

    def to_dict(self) -> dict:
        """辞書に変換する."""
        return {
            "data_analysis": self.data_analysis,
            "pace_reading": self.pace_reading,
            "risk_management": self.risk_management,
            "intuition": self.intuition,
        }
