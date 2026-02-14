"""GetRaceDetailUseCaseのテスト."""
from datetime import date, datetime

import pytest

from src.domain.identifiers import RaceId
from src.domain.ports import (
    CourseAptitudeData,
    ExtendedPedigreeData,
    GatePositionStatsData,
    HorsePerformanceData,
    JockeyInfoData,
    JockeyStatsData,
    JockeyStatsDetailData,
    OddsHistoryData,
    PastRaceStats,
    PedigreeData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
    StallionConditionStatsData,
    StallionDistanceStatsData,
    StallionOffspringStatsData,
    StallionTrackStatsData,
    TopOffspringData,
    TrainerClassStatsData,
    TrainerInfoData,
    TrainerStatsDetailData,
    TrainerTrackStatsData,
    TrainingRecordData,
    TrainingSummaryData,
    WeightData,
    BreederInfoData,
    BreederStatsData,
    OwnerInfoData,
    OwnerStatsData,
    RaceResultsData,
)


class MockRaceDataProvider(RaceDataProvider):
    """テスト用のモック実装."""

    def __init__(self) -> None:
        self._races: dict[str, RaceData] = {}
        self._runners: dict[str, list[RunnerData]] = {}

    def add_race(self, race: RaceData) -> None:
        """テスト用にレースを追加."""
        self._races[race.race_id] = race

    def add_runners(self, race_id: str, runners: list[RunnerData]) -> None:
        """テスト用に出走馬を追加."""
        self._runners[race_id] = runners

    def get_race(self, race_id: RaceId) -> RaceData | None:
        return self._races.get(str(race_id))

    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        return []

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        return self._runners.get(str(race_id), [])

    def get_past_performance(self, horse_id: str) -> list[PerformanceData]:
        return []

    def get_jockey_stats(self, jockey_id: str, course: str) -> JockeyStatsData | None:
        return None

    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        return None

    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        return []

    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        return {}

    def get_jra_checksum(
        self,
        venue_code: str,
        kaisai_kai: str,
        kaisai_nichime: int,
        race_number: int,
    ) -> int | None:
        return None

    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        return []

    def get_past_race_stats(
        self,
        track_type: str,
        distance: int,
        grade_class: str | None = None,
        limit: int = 100
    ) -> PastRaceStats | None:
        """過去の同条件レース統計を取得する（モック実装）."""
        return None

    def get_jockey_info(self, jockey_id: str) -> JockeyInfoData | None:
        """騎手基本情報を取得する（モック実装）."""
        return None

    def get_jockey_stats_detail(
        self,
        jockey_id: str,
        year: int | None = None,
        period: str = "recent",
    ) -> JockeyStatsDetailData | None:
        """騎手成績統計を取得する（モック実装）."""
        return None

    def get_horse_performances(
        self,
        horse_id: str,
        limit: int = 5,
        track_type: str | None = None,
    ) -> list[HorsePerformanceData]:
        """馬の過去成績を取得する（モック実装）."""
        return []

    def get_horse_training(
        self,
        horse_id: str,
        limit: int = 5,
        days: int = 30,
    ) -> tuple[list[TrainingRecordData], TrainingSummaryData | None]:
        """馬の調教データを取得する（モック実装）."""
        return [], None

    def get_extended_pedigree(self, horse_id: str) -> ExtendedPedigreeData | None:
        """馬の拡張血統情報を取得する（モック実装）."""
        return None

    def get_odds_history(self, race_id: RaceId) -> OddsHistoryData | None:
        """レースのオッズ履歴を取得する（モック実装）."""
        return None

    def get_course_aptitude(self, horse_id: str) -> CourseAptitudeData | None:
        """馬のコース適性を取得する（モック実装）."""
        return None

    def get_stallion_offspring_stats(
        self,
        stallion_id: str,
        year: int | None = None,
        track_type: str | None = None,
    ) -> tuple[
        StallionOffspringStatsData | None,
        list[StallionTrackStatsData],
        list[StallionDistanceStatsData],
        list[StallionConditionStatsData],
        list[TopOffspringData],
    ]:
        """種牡馬産駒成績を取得する（モック実装）."""
        return None, [], [], [], []

    def get_trainer_info(self, trainer_id: str) -> TrainerInfoData | None:
        """厩舎基本情報を取得する（モック実装）."""
        return None

    def get_trainer_stats_detail(
        self,
        trainer_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> tuple[TrainerStatsDetailData | None, list[TrainerTrackStatsData], list[TrainerClassStatsData]]:
        """厩舎成績統計を取得する（モック実装）."""
        return None, [], []

    def get_gate_position_stats(
        self,
        venue: str,
        track_type: str | None = None,
        distance: int | None = None,
        track_condition: str | None = None,
        limit: int = 100,
    ) -> GatePositionStatsData | None:
        """枠順別成績統計を取得する（モック実装）."""
        return None

    def get_race_results(self, race_id: RaceId) -> RaceResultsData | None:
        """レース結果・払戻金を取得する（モック実装）."""
        return None

    def get_owner_info(self, owner_id: str) -> OwnerInfoData | None:
        """馬主基本情報を取得する（モック実装）."""
        return None

    def get_owner_stats(
        self,
        owner_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> OwnerStatsData | None:
        """馬主成績統計を取得する（モック実装）."""
        return None

    def get_breeder_info(self, breeder_id: str) -> BreederInfoData | None:
        """生産者基本情報を取得する（モック実装）."""
        return None

    def get_breeder_stats(
        self,
        breeder_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> BreederStatsData | None:
        """生産者成績統計を取得する（モック実装）."""
        return None

    def get_running_styles(self, race_id):
        return []


class TestGetRaceDetailUseCase:
    """GetRaceDetailUseCaseの単体テスト."""

    def test_レースIDでレース詳細を取得できる(self) -> None:
        """レースIDでレース詳細を取得できることを確認."""
        from src.application.use_cases.get_race_detail import GetRaceDetailUseCase

        provider = MockRaceDataProvider()
        race = RaceData(
            race_id="2024060111",
            race_name="日本ダービー",
            race_number=11,
            venue="東京",
            start_time=datetime(2024, 6, 1, 15, 40),
            betting_deadline=datetime(2024, 6, 1, 15, 35),
            track_condition="良",
        )
        runners = [
            RunnerData(
                horse_number=1,
                horse_name="ダノンデサイル",
                horse_id="horse1",
                jockey_name="横山武史",
                jockey_id="jockey1",
                odds="3.5",
                popularity=1,
            ),
            RunnerData(
                horse_number=2,
                horse_name="ジャスティンミラノ",
                horse_id="horse2",
                jockey_name="戸崎圭太",
                jockey_id="jockey2",
                odds="4.2",
                popularity=2,
            ),
        ]
        provider.add_race(race)
        provider.add_runners("2024060111", runners)
        use_case = GetRaceDetailUseCase(provider)

        result = use_case.execute(RaceId("2024060111"))

        assert result is not None
        assert result.race.race_name == "日本ダービー"
        assert len(result.runners) == 2
        assert result.runners[0].horse_name == "ダノンデサイル"

    def test_存在しないレースIDでNoneを返す(self) -> None:
        """存在しないレースIDでNoneが返ることを確認."""
        from src.application.use_cases.get_race_detail import GetRaceDetailUseCase

        provider = MockRaceDataProvider()
        use_case = GetRaceDetailUseCase(provider)

        result = use_case.execute(RaceId("nonexistent"))

        assert result is None

    def test_出走馬がいないレースでも詳細を取得できる(self) -> None:
        """出走馬がいないレースでも詳細を取得できることを確認."""
        from src.application.use_cases.get_race_detail import GetRaceDetailUseCase

        provider = MockRaceDataProvider()
        race = RaceData(
            race_id="2024060111",
            race_name="日本ダービー",
            race_number=11,
            venue="東京",
            start_time=datetime(2024, 6, 1, 15, 40),
            betting_deadline=datetime(2024, 6, 1, 15, 35),
            track_condition="良",
        )
        provider.add_race(race)
        use_case = GetRaceDetailUseCase(provider)

        result = use_case.execute(RaceId("2024060111"))

        assert result is not None
        assert result.race.race_name == "日本ダービー"
        assert result.runners == []
