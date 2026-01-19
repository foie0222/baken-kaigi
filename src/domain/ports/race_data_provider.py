"""レースデータ取得インターフェース（ポート）."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from ..identifiers import RaceId


@dataclass(frozen=True)
class RaceData:
    """レース情報."""

    race_id: str
    race_name: str
    race_number: int
    venue: str
    start_time: datetime
    betting_deadline: datetime
    track_condition: str  # 馬場状態


@dataclass(frozen=True)
class RunnerData:
    """出走馬情報."""

    horse_number: int
    horse_name: str
    horse_id: str
    jockey_name: str
    jockey_id: str
    odds: str
    popularity: int


@dataclass(frozen=True)
class PerformanceData:
    """過去成績データ."""

    race_date: datetime
    race_name: str
    venue: str
    finish_position: int
    distance: int
    track_condition: str
    time: str


@dataclass(frozen=True)
class JockeyStatsData:
    """騎手のコース成績データ."""

    jockey_id: str
    jockey_name: str
    course: str
    total_races: int
    wins: int
    win_rate: float
    place_rate: float


class RaceDataProvider(ABC):
    """レースデータ取得インターフェース（外部システム）."""

    @abstractmethod
    def get_race(self, race_id: RaceId) -> RaceData | None:
        """レース情報を取得する."""
        pass

    @abstractmethod
    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        """出走馬情報を取得する."""
        pass

    @abstractmethod
    def get_past_performance(self, horse_id: str) -> list[PerformanceData]:
        """馬の過去成績を取得する."""
        pass

    @abstractmethod
    def get_jockey_stats(self, jockey_id: str, course: str) -> JockeyStatsData | None:
        """騎手のコース成績を取得する."""
        pass
