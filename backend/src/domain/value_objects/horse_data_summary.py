"""馬のデータ要約を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HorseDataSummary:
    """個々の馬に関するデータ要約."""

    horse_number: int
    horse_name: str
    recent_results: str  # 過去5走の成績要約
    jockey_stats: str  # 騎手の当該コース成績
    track_suitability: str  # 馬場適性コメント
    current_odds: str  # 現在のオッズ
    popularity: int  # 人気順
    pedigree: str | None = None        # "父:〇〇 母父:△△"
    weight_trend: str | None = None    # "増加傾向" / "安定" / "減少傾向"
    weight_current: int | None = None  # 現在の馬体重

    def __post_init__(self) -> None:
        """バリデーション."""
        if not 1 <= self.horse_number <= 18:
            raise ValueError("Horse number must be between 1 and 18")
        if not self.horse_name:
            raise ValueError("Horse name cannot be empty")
        if self.popularity < 1:
            raise ValueError("Popularity must be at least 1")
