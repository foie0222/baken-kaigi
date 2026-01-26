"""RaceDataProviderのテスト."""
from datetime import date, datetime

import pytest

from src.domain.identifiers import RaceId
from src.domain.ports import (
    CourseAptitudeData,
    ExtendedPedigreeData,
    HorsePerformanceData,
    JockeyInfoData,
    JockeyStatsDetailData,
    PastRaceStats,
    PedigreeData,
    PopularityStats,
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
)


class MockRaceDataProvider(RaceDataProvider):
    """テスト用のモック実装."""

    def __init__(self) -> None:
        self._races: dict[str, RaceData] = {}
        self._races_by_date: dict[date, list[RaceData]] = {}
        self._runners: dict[str, list[RunnerData]] = {}
        self._pedigrees: dict[str, PedigreeData] = {}
        self._weight_histories: dict[str, list[WeightData]] = {}
        self._race_weights: dict[str, dict[int, WeightData]] = {}

    def add_race(self, race: RaceData) -> None:
        """テスト用にレースを追加."""
        self._races[race.race_id] = race
        race_date = race.start_time.date()
        if race_date not in self._races_by_date:
            self._races_by_date[race_date] = []
        self._races_by_date[race_date].append(race)

    def add_runners(self, race_id: str, runners: list[RunnerData]) -> None:
        """テスト用に出走馬を追加."""
        self._runners[race_id] = runners

    def add_pedigree(self, horse_id: str, pedigree: PedigreeData) -> None:
        """テスト用に血統情報を追加."""
        self._pedigrees[horse_id] = pedigree

    def add_weight_history(self, horse_id: str, weights: list[WeightData]) -> None:
        """テスト用に馬体重履歴を追加."""
        self._weight_histories[horse_id] = weights

    def add_race_weights(self, race_id: str, weights: dict[int, WeightData]) -> None:
        """テスト用にレースの馬体重情報を追加."""
        self._race_weights[race_id] = weights

    def get_race(self, race_id: RaceId) -> RaceData | None:
        """レース情報を取得する."""
        return self._races.get(str(race_id))

    def get_races_by_date(self, target_date: date, venue: str | None = None) -> list[RaceData]:
        """日付でレース一覧を取得する."""
        races = self._races_by_date.get(target_date, [])
        if venue:
            races = [r for r in races if r.venue == venue]
        return sorted(races, key=lambda r: (r.venue, r.race_number))

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        """出走馬情報を取得する."""
        return self._runners.get(str(race_id), [])

    def get_past_performance(self, horse_id: str) -> list:
        """馬の過去成績を取得する."""
        return []

    def get_jockey_stats(self, jockey_id: str, course: str):
        """騎手のコース成績を取得する."""
        return None

    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        """馬の血統情報を取得する."""
        return self._pedigrees.get(horse_id)

    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        """馬の体重履歴を取得する."""
        weights = self._weight_histories.get(horse_id, [])
        return weights[:limit]

    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        """レースの馬体重情報を取得する."""
        return self._race_weights.get(str(race_id), {})

    def get_jra_checksum(
        self,
        venue_code: str,
        kaisai_kai: str,
        kaisai_nichime: int,
        race_number: int,
    ) -> int | None:
        """JRA出馬表URLのチェックサムを取得する（モック実装）."""
        return None

    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        """開催日一覧を取得する."""
        dates = list(self._races_by_date.keys())
        if from_date:
            dates = [d for d in dates if d >= from_date]
        if to_date:
            dates = [d for d in dates if d <= to_date]
        return sorted(dates, reverse=True)

    def get_past_race_stats(
        self,
        track_type: str,
        distance: int,
        grade_class: str | None = None,
        limit: int = 100
    ) -> PastRaceStats | None:
        """過去の同条件レース統計を取得する（モック実装）."""
        return PastRaceStats(
            total_races=limit,
            popularity_stats=[
                PopularityStats(
                    popularity=1,
                    total_runs=100,
                    wins=33,
                    places=60,
                    win_rate=33.0,
                    place_rate=60.0,
                ),
            ],
            avg_win_payout=350.0,
            avg_place_payout=150.0,
            track_type=track_type,
            distance=distance,
            grade_class=grade_class,
        )

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


class TestRaceDataProviderInterface:
    """RaceDataProviderインターフェースのテスト."""

    def test_get_races_by_dateで日付指定でレース一覧を取得できる(self) -> None:
        """get_races_by_dateで日付を指定してレース一覧を取得できることを確認."""
        provider = MockRaceDataProvider()
        target_date = date(2024, 6, 1)
        race1 = RaceData(
            race_id="2024060101",
            race_name="1R",
            race_number=1,
            venue="東京",
            start_time=datetime(2024, 6, 1, 10, 0),
            betting_deadline=datetime(2024, 6, 1, 9, 55),
            track_condition="良",
        )
        race2 = RaceData(
            race_id="2024060102",
            race_name="2R",
            race_number=2,
            venue="東京",
            start_time=datetime(2024, 6, 1, 10, 30),
            betting_deadline=datetime(2024, 6, 1, 10, 25),
            track_condition="良",
        )
        provider.add_race(race1)
        provider.add_race(race2)

        races = provider.get_races_by_date(target_date)

        assert len(races) == 2
        assert races[0].race_number == 1
        assert races[1].race_number == 2

    def test_get_races_by_dateで開催場フィルタできる(self) -> None:
        """get_races_by_dateで開催場でフィルタできることを確認."""
        provider = MockRaceDataProvider()
        target_date = date(2024, 6, 1)
        tokyo_race = RaceData(
            race_id="2024060101",
            race_name="東京1R",
            race_number=1,
            venue="東京",
            start_time=datetime(2024, 6, 1, 10, 0),
            betting_deadline=datetime(2024, 6, 1, 9, 55),
            track_condition="良",
        )
        kyoto_race = RaceData(
            race_id="2024060201",
            race_name="京都1R",
            race_number=1,
            venue="京都",
            start_time=datetime(2024, 6, 1, 10, 0),
            betting_deadline=datetime(2024, 6, 1, 9, 55),
            track_condition="良",
        )
        provider.add_race(tokyo_race)
        provider.add_race(kyoto_race)

        tokyo_races = provider.get_races_by_date(target_date, venue="東京")

        assert len(tokyo_races) == 1
        assert tokyo_races[0].venue == "東京"

    def test_get_races_by_dateでレースがない日は空リスト(self) -> None:
        """get_races_by_dateでレースがない日は空リストが返ることを確認."""
        provider = MockRaceDataProvider()
        target_date = date(2024, 6, 1)

        races = provider.get_races_by_date(target_date)

        assert races == []


class TestPedigreeInterface:
    """get_pedigreeインターフェースのテスト."""

    def test_get_pedigreeで血統情報を取得できる(self) -> None:
        """get_pedigreeで血統情報を取得できることを確認."""
        provider = MockRaceDataProvider()
        pedigree = PedigreeData(
            horse_id="horse1",
            horse_name="テストホース",
            sire_name="ディープインパクト",
            dam_name="マイママ",
            broodmare_sire="サンデーサイレンス",
        )
        provider.add_pedigree("horse1", pedigree)

        result = provider.get_pedigree("horse1")

        assert result is not None
        assert result.horse_id == "horse1"
        assert result.horse_name == "テストホース"
        assert result.sire_name == "ディープインパクト"
        assert result.dam_name == "マイママ"
        assert result.broodmare_sire == "サンデーサイレンス"

    def test_get_pedigreeで存在しない馬はNone(self) -> None:
        """get_pedigreeで存在しない馬はNoneが返ることを確認."""
        provider = MockRaceDataProvider()

        result = provider.get_pedigree("nonexistent")

        assert result is None


class TestWeightHistoryInterface:
    """get_weight_historyインターフェースのテスト."""

    def test_get_weight_historyで馬体重履歴を取得できる(self) -> None:
        """get_weight_historyで馬体重履歴を取得できることを確認."""
        provider = MockRaceDataProvider()
        weights = [
            WeightData(weight=480, weight_diff=2),
            WeightData(weight=478, weight_diff=-4),
            WeightData(weight=482, weight_diff=0),
        ]
        provider.add_weight_history("horse1", weights)

        result = provider.get_weight_history("horse1")

        assert len(result) == 3
        assert result[0].weight == 480
        assert result[0].weight_diff == 2
        assert result[1].weight == 478
        assert result[1].weight_diff == -4

    def test_get_weight_historyでlimit指定できる(self) -> None:
        """get_weight_historyでlimitを指定して件数を制限できることを確認."""
        provider = MockRaceDataProvider()
        weights = [
            WeightData(weight=480, weight_diff=2),
            WeightData(weight=478, weight_diff=-4),
            WeightData(weight=482, weight_diff=0),
            WeightData(weight=484, weight_diff=2),
            WeightData(weight=486, weight_diff=2),
        ]
        provider.add_weight_history("horse1", weights)

        result = provider.get_weight_history("horse1", limit=3)

        assert len(result) == 3

    def test_get_weight_historyで存在しない馬は空リスト(self) -> None:
        """get_weight_historyで存在しない馬は空リストが返ることを確認."""
        provider = MockRaceDataProvider()

        result = provider.get_weight_history("nonexistent")

        assert result == []


class TestRaceWeightsInterface:
    """get_race_weightsインターフェースのテスト."""

    def test_get_race_weightsでレースの馬体重を取得できる(self) -> None:
        """get_race_weightsでレースの馬体重情報を取得できることを確認."""
        provider = MockRaceDataProvider()
        race_weights = {
            1: WeightData(weight=480, weight_diff=2),
            2: WeightData(weight=456, weight_diff=-4),
            3: WeightData(weight=502, weight_diff=0),
        }
        provider.add_race_weights("2024060111", race_weights)

        result = provider.get_race_weights(RaceId("2024060111"))

        assert len(result) == 3
        assert result[1].weight == 480
        assert result[1].weight_diff == 2
        assert result[2].weight == 456
        assert result[3].weight == 502

    def test_get_race_weightsで存在しないレースは空辞書(self) -> None:
        """get_race_weightsで存在しないレースは空辞書が返ることを確認."""
        provider = MockRaceDataProvider()

        result = provider.get_race_weights(RaceId("nonexistent"))

        assert result == {}
