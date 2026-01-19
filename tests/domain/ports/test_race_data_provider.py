"""RaceDataProviderのテスト."""
from datetime import date, datetime

import pytest

from src.domain.identifiers import RaceId
from src.domain.ports import RaceData, RaceDataProvider, RunnerData


class MockRaceDataProvider(RaceDataProvider):
    """テスト用のモック実装."""

    def __init__(self) -> None:
        self._races: dict[str, RaceData] = {}
        self._races_by_date: dict[date, list[RaceData]] = {}
        self._runners: dict[str, list[RunnerData]] = {}

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
