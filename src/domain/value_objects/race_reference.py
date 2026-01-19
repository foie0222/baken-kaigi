"""レースへの参照情報を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..identifiers import RaceId


@dataclass(frozen=True)
class RaceReference:
    """外部のレース情報への参照（表示用の基本情報をキャッシュとして保持）."""

    race_id: RaceId
    race_name: str
    race_number: int
    venue: str
    start_time: datetime
    betting_deadline: datetime

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.race_name:
            raise ValueError("Race name cannot be empty")
        if not 1 <= self.race_number <= 12:
            raise ValueError("Race number must be between 1 and 12")
        if not self.venue:
            raise ValueError("Venue cannot be empty")
        if self.betting_deadline > self.start_time:
            raise ValueError("Betting deadline must be before start time")

    def is_before_deadline(self, now: datetime) -> bool:
        """締め切り前かどうか判定."""
        return now < self.betting_deadline

    def get_remaining_time(self, now: datetime) -> timedelta | None:
        """締め切りまでの残り時間を取得（締め切り後はNone）."""
        if now >= self.betting_deadline:
            return None
        return self.betting_deadline - now

    def to_display_string(self) -> str:
        """表示用文字列（例: "東京11R 日本ダービー"）."""
        return f"{self.venue}{self.race_number}R {self.race_name}"

    def __str__(self) -> str:
        """文字列表現."""
        return self.to_display_string()
