"""GetRaceListUseCaseのテスト."""
from dataclasses import dataclass
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
        self._races_by_date: dict[date, list[RaceData]] = {}

    def add_race(self, race: RaceData) -> None:
        """テスト用にレースを追加."""
        self._races[race.race_id] = race
        race_date = race.start_time.date()
        if race_date not in self._races_by_date:
            self._races_by_date[race_date] = []
        self._races_by_date[race_date].append(race)

    def get_race(self, race_id: RaceId) -> RaceData | None:
        return self._races.get(str(race_id))

    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        races = self._races_by_date.get(target_date, [])
        if venue:
            races = [r for r in races if r.venue == venue]
        return sorted(races, key=lambda r: (r.venue, r.race_number))

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        return []

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
        dates = list(self._races_by_date.keys())
        if from_date:
            dates = [d for d in dates if d >= from_date]
        if to_date:
            dates = [d for d in dates if d <= to_date]
        return sorted(dates, reverse=True)


class TestGetRaceListUseCase:
    """GetRaceListUseCaseの単体テスト."""

    def test_日付を指定してレース一覧を取得できる(self) -> None:
        """日付を指定してレース一覧を取得できることを確認."""
        from src.application.use_cases.get_race_list import GetRaceListUseCase

        provider = MockRaceDataProvider()
        provider.add_race(
            RaceData(
                race_id="2024060101",
                race_name="未勝利",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 6, 1, 10, 0),
                betting_deadline=datetime(2024, 6, 1, 9, 55),
                track_condition="良",
            )
        )
        provider.add_race(
            RaceData(
                race_id="2024060111",
                race_name="日本ダービー",
                race_number=11,
                venue="東京",
                start_time=datetime(2024, 6, 1, 15, 40),
                betting_deadline=datetime(2024, 6, 1, 15, 35),
                track_condition="良",
            )
        )
        use_case = GetRaceListUseCase(provider)

        result = use_case.execute(date(2024, 6, 1))

        assert len(result.races) == 2
        assert result.races[0].race_number == 1
        assert result.races[1].race_name == "日本ダービー"

    def test_開催場でフィルタできる(self) -> None:
        """開催場でフィルタできることを確認."""
        from src.application.use_cases.get_race_list import GetRaceListUseCase

        provider = MockRaceDataProvider()
        provider.add_race(
            RaceData(
                race_id="2024060101",
                race_name="東京1R",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 6, 1, 10, 0),
                betting_deadline=datetime(2024, 6, 1, 9, 55),
                track_condition="良",
            )
        )
        provider.add_race(
            RaceData(
                race_id="2024060201",
                race_name="京都1R",
                race_number=1,
                venue="京都",
                start_time=datetime(2024, 6, 1, 10, 0),
                betting_deadline=datetime(2024, 6, 1, 9, 55),
                track_condition="良",
            )
        )
        use_case = GetRaceListUseCase(provider)

        result = use_case.execute(date(2024, 6, 1), venue="東京")

        assert len(result.races) == 1
        assert result.races[0].venue == "東京"

    def test_レースがない日は空リスト(self) -> None:
        """レースがない日は空リストが返ることを確認."""
        from src.application.use_cases.get_race_list import GetRaceListUseCase

        provider = MockRaceDataProvider()
        use_case = GetRaceListUseCase(provider)

        result = use_case.execute(date(2024, 6, 1))

        assert result.races == []

    def test_結果に開催場一覧が含まれる(self) -> None:
        """結果に開催場一覧が含まれることを確認."""
        from src.application.use_cases.get_race_list import GetRaceListUseCase

        provider = MockRaceDataProvider()
        provider.add_race(
            RaceData(
                race_id="2024060101",
                race_name="東京1R",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 6, 1, 10, 0),
                betting_deadline=datetime(2024, 6, 1, 9, 55),
                track_condition="良",
            )
        )
        provider.add_race(
            RaceData(
                race_id="2024060201",
                race_name="京都1R",
                race_number=1,
                venue="京都",
                start_time=datetime(2024, 6, 1, 10, 0),
                betting_deadline=datetime(2024, 6, 1, 9, 55),
                track_condition="良",
            )
        )
        use_case = GetRaceListUseCase(provider)

        result = use_case.execute(date(2024, 6, 1))

        assert set(result.venues) == {"東京", "京都"}
