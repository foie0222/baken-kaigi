"""GetRaceDetailUseCaseのテスト."""
from datetime import date, datetime

import pytest

from src.domain.identifiers import RaceId
from src.domain.ports import (
    JockeyStatsData,
    PedigreeData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
    WeightData,
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
