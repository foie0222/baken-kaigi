"""レースデータ取得インターフェース（ポート）."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

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
    track_type: str = ""  # コース種別（芝/ダ/障）
    distance: int = 0  # 距離（メートル）
    horse_count: int = 0  # 出走頭数


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
    waku_ban: int = 0  # 枠番（1-8）


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


@dataclass(frozen=True)
class PedigreeData:
    """血統情報."""

    horse_id: str
    horse_name: str | None
    sire_name: str | None       # 父
    dam_name: str | None        # 母
    broodmare_sire: str | None  # 母父


@dataclass(frozen=True)
class WeightData:
    """馬体重データ."""

    weight: int          # 馬体重(kg)
    weight_diff: int     # 前走比増減


class RaceDataProvider(ABC):
    """レースデータ取得インターフェース（外部システム）."""

    @abstractmethod
    def get_race(self, race_id: RaceId) -> RaceData | None:
        """レース情報を取得する."""
        pass

    @abstractmethod
    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        """日付でレース一覧を取得する.

        Args:
            target_date: 対象日付
            venue: 開催場（指定しない場合は全開催場）

        Returns:
            レース一覧（開催場、レース番号順）
        """
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

    @abstractmethod
    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        """馬の血統情報を取得する."""
        pass

    @abstractmethod
    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        """馬の体重履歴を取得する."""
        pass

    @abstractmethod
    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        """レースの馬体重情報を取得する.

        Returns:
            馬番をキーとした馬体重データの辞書
        """
        pass
