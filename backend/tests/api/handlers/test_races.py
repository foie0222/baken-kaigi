"""レースAPIハンドラーのテスト."""
import json
from datetime import date, datetime

import pytest

from src.api.dependencies import Dependencies
from src.domain.identifiers import RaceId
from src.domain.ports import (
    JockeyStatsData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
)


class MockRaceDataProvider(RaceDataProvider):
    """テスト用のモックレースデータプロバイダ."""

    def __init__(self) -> None:
        self._races: dict[str, RaceData] = {}
        self._races_by_date: dict[date, list[RaceData]] = {}
        self._runners: dict[str, list[RunnerData]] = {}

    def add_race(self, race: RaceData) -> None:
        self._races[race.race_id] = race
        race_date = race.start_time.date()
        if race_date not in self._races_by_date:
            self._races_by_date[race_date] = []
        self._races_by_date[race_date].append(race)

    def add_runners(self, race_id: str, runners: list[RunnerData]) -> None:
        self._runners[race_id] = runners

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
        return self._runners.get(str(race_id), [])

    def get_past_performance(self, horse_id: str) -> list[PerformanceData]:
        return []

    def get_jockey_stats(self, jockey_id: str, course: str) -> JockeyStatsData | None:
        return None

    def get_pedigree(self, horse_id: str):
        return None

    def get_weight_history(self, horse_id: str, limit: int = 5):
        return []

    def get_race_weights(self, race_id: RaceId):
        return {}


@pytest.fixture(autouse=True)
def reset_dependencies():
    """各テスト前に依存性をリセット."""
    Dependencies.reset()
    yield
    Dependencies.reset()


class TestGetRacesHandler:
    """GET /races ハンドラーのテスト."""

    def test_レース一覧を取得できる(self) -> None:
        """レース一覧を取得できることを確認."""
        from src.api.handlers.races import get_races

        provider = MockRaceDataProvider()
        provider.add_race(
            RaceData(
                race_id="2024060101",
                race_name="1R",
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
        Dependencies.set_race_data_provider(provider)

        event = {
            "queryStringParameters": {"date": "2024-06-01"},
        }

        response = get_races(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["races"]) == 2
        assert body["races"][0]["race_name"] == "1R"
        assert body["races"][1]["race_name"] == "日本ダービー"

    def test_レース一覧にコース情報が含まれる(self) -> None:
        """レース一覧にtrack_type, distance, horse_countが含まれることを確認."""
        from src.api.handlers.races import get_races

        provider = MockRaceDataProvider()
        provider.add_race(
            RaceData(
                race_id="2024060101",
                race_name="3歳未勝利",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 6, 1, 10, 0),
                betting_deadline=datetime(2024, 6, 1, 9, 55),
                track_condition="良",
                track_type="芝",
                distance=1600,
                horse_count=16,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "queryStringParameters": {"date": "2024-06-01"},
        }

        response = get_races(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["races"]) == 1
        race = body["races"][0]
        assert race["track_type"] == "芝"
        assert race["distance"] == 1600
        assert race["horse_count"] == 16

    def test_開催場でフィルタできる(self) -> None:
        """開催場でフィルタできることを確認."""
        from src.api.handlers.races import get_races

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
        Dependencies.set_race_data_provider(provider)

        event = {
            "queryStringParameters": {"date": "2024-06-01", "venue": "東京"},
        }

        response = get_races(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["races"]) == 1
        assert body["races"][0]["venue"] == "東京"

    def test_日付パラメータがないとエラー(self) -> None:
        """日付パラメータがないとエラーになることを確認."""
        from src.api.handlers.races import get_races

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"queryStringParameters": None}

        response = get_races(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "date" in body["error"]["message"].lower()


class TestGetRaceDetailHandler:
    """GET /races/{race_id} ハンドラーのテスト."""

    def test_レース詳細を取得できる(self) -> None:
        """レース詳細を取得できることを確認."""
        from src.api.handlers.races import get_race_detail

        provider = MockRaceDataProvider()
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
        provider.add_runners(
            "2024060111",
            [
                RunnerData(
                    horse_number=1,
                    horse_name="ダノンデサイル",
                    horse_id="horse1",
                    jockey_name="横山武史",
                    jockey_id="jockey1",
                    odds="3.5",
                    popularity=1,
                ),
            ],
        )
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"race_id": "2024060111"}}

        response = get_race_detail(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["race"]["race_name"] == "日本ダービー"
        assert len(body["runners"]) == 1
        assert body["runners"][0]["horse_name"] == "ダノンデサイル"

    def test_存在しないレースで404(self) -> None:
        """存在しないレースで404が返ることを確認."""
        from src.api.handlers.races import get_race_detail

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"race_id": "nonexistent"}}

        response = get_race_detail(event, None)

        assert response["statusCode"] == 404

    def test_レース詳細にコース情報が含まれる(self) -> None:
        """レース詳細にtrack_type, distance, horse_countが含まれることを確認."""
        from src.api.handlers.races import get_race_detail

        provider = MockRaceDataProvider()
        provider.add_race(
            RaceData(
                race_id="2024060111",
                race_name="日本ダービー",
                race_number=11,
                venue="東京",
                start_time=datetime(2024, 6, 1, 15, 40),
                betting_deadline=datetime(2024, 6, 1, 15, 35),
                track_condition="良",
                track_type="芝",
                distance=2400,
                horse_count=18,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"race_id": "2024060111"}}

        response = get_race_detail(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["race"]["track_type"] == "芝"
        assert body["race"]["distance"] == 2400
        assert body["race"]["horse_count"] == 18
