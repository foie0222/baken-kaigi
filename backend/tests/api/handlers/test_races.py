"""レースAPIハンドラーのテスト."""
import json
from datetime import date, datetime

import pytest

from src.api.dependencies import Dependencies
from src.domain.identifiers import RaceId
from src.domain.ports import (
    PastRaceStats,
    JockeyStatsData,
    PedigreeData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
    WeightData,
)


class MockRaceDataProvider(RaceDataProvider):
    """テスト用のモックレースデータプロバイダ."""

    def __init__(self) -> None:
        self._races: dict[str, RaceData] = {}
        self._races_by_date: dict[date, list[RaceData]] = {}
        self._runners: dict[str, list[RunnerData]] = {}
        self._race_weights: dict[str, dict[int, WeightData]] = {}

    def add_race(self, race: RaceData) -> None:
        self._races[race.race_id] = race
        race_date = race.start_time.date()
        if race_date not in self._races_by_date:
            self._races_by_date[race_date] = []
        self._races_by_date[race_date].append(race)

    def add_runners(self, race_id: str, runners: list[RunnerData]) -> None:
        self._runners[race_id] = runners

    def add_race_weights(self, race_id: str, weights: dict[int, WeightData]) -> None:
        self._race_weights[race_id] = weights

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

    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        return None

    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        return []

    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        return self._race_weights.get(str(race_id), {})

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

    def get_past_race_stats(
        self,
        track_type: str,
        distance: int,
        grade_class: str | None = None,
        limit: int = 100
    ) -> PastRaceStats | None:
        """過去の同条件レース統計を取得する（モック実装）."""
        return None


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

    def test_レース一覧に条件情報が含まれる(self) -> None:
        """レース一覧にgrade_class, age_condition, is_obstacleが含まれることを確認."""
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
                grade_class="未勝利",
                age_condition="3歳",
                is_obstacle=False,
            )
        )
        provider.add_race(
            RaceData(
                race_id="2024060102",
                race_name="日本ダービー",
                race_number=11,
                venue="東京",
                start_time=datetime(2024, 6, 1, 15, 40),
                betting_deadline=datetime(2024, 6, 1, 15, 35),
                track_condition="良",
                grade_class="G1",
                age_condition="3歳",
                is_obstacle=False,
            )
        )
        provider.add_race(
            RaceData(
                race_id="2024060103",
                race_name="障害未勝利",
                race_number=4,
                venue="東京",
                start_time=datetime(2024, 6, 1, 11, 35),
                betting_deadline=datetime(2024, 6, 1, 11, 30),
                track_condition="良",
                grade_class="未勝利",
                age_condition="4歳以上",
                is_obstacle=True,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "queryStringParameters": {"date": "2024-06-01"},
        }

        response = get_races(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["races"]) == 3

        # 未勝利レース
        race1 = body["races"][0]
        assert race1["grade_class"] == "未勝利"
        assert race1["age_condition"] == "3歳"
        assert race1["is_obstacle"] is False

        # G1レース
        race2 = body["races"][2]
        assert race2["grade_class"] == "G1"
        assert race2["age_condition"] == "3歳"
        assert race2["is_obstacle"] is False

        # 障害レース
        race3 = body["races"][1]
        assert race3["grade_class"] == "未勝利"
        assert race3["age_condition"] == "4歳以上"
        assert race3["is_obstacle"] is True

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

    def test_レース詳細に条件情報が含まれる(self) -> None:
        """レース詳細にgrade_class, age_condition, is_obstacleが含まれることを確認."""
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
                grade_class="G1",
                age_condition="3歳",
                is_obstacle=False,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"race_id": "2024060111"}}

        response = get_race_detail(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["race"]["grade_class"] == "G1"
        assert body["race"]["age_condition"] == "3歳"
        assert body["race"]["is_obstacle"] is False

    def test_障害レースの詳細が正しく取得できる(self) -> None:
        """障害レースの詳細が正しく取得できることを確認."""
        from src.api.handlers.races import get_race_detail

        provider = MockRaceDataProvider()
        provider.add_race(
            RaceData(
                race_id="2024060104",
                race_name="障害オープン",
                race_number=4,
                venue="中山",
                start_time=datetime(2024, 6, 1, 11, 35),
                betting_deadline=datetime(2024, 6, 1, 11, 30),
                track_condition="良",
                track_type="障害",
                distance=3350,
                horse_count=14,
                grade_class="OP",
                age_condition="4歳以上",
                is_obstacle=True,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"race_id": "2024060104"}}

        response = get_race_detail(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["race"]["grade_class"] == "OP"
        assert body["race"]["age_condition"] == "4歳以上"
        assert body["race"]["is_obstacle"] is True
        assert body["race"]["track_type"] == "障害"

    def test_レース詳細に馬体重が含まれる(self) -> None:
        """馬体重データが存在する場合、レスポンスにweight, weight_diffが含まれることを確認."""
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
                RunnerData(
                    horse_number=2,
                    horse_name="レガレイラ",
                    horse_id="horse2",
                    jockey_name="北村宏司",
                    jockey_id="jockey2",
                    odds="5.0",
                    popularity=2,
                ),
            ],
        )
        provider.add_race_weights(
            "2024060111",
            {
                1: WeightData(weight=480, weight_diff=4),
                2: WeightData(weight=456, weight_diff=-2),
            },
        )
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"race_id": "2024060111"}}

        response = get_race_detail(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["runners"]) == 2

        runner1 = body["runners"][0]
        assert runner1["weight"] == 480
        assert runner1["weight_diff"] == 4

        runner2 = body["runners"][1]
        assert runner2["weight"] == 456
        assert runner2["weight_diff"] == -2

    def test_馬体重データがない場合はweightフィールドが含まれない(self) -> None:
        """馬体重データが存在しない場合、レスポンスにweightフィールドが含まれないことを確認."""
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
        # 馬体重データを設定しない
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"race_id": "2024060111"}}

        response = get_race_detail(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["runners"]) == 1

        runner = body["runners"][0]
        assert "weight" not in runner
        assert "weight_diff" not in runner


class TestGetRaceDatesHandler:
    """GET /race-dates ハンドラーのテスト."""

    def test_開催日一覧を取得できる(self) -> None:
        """開催日一覧を取得できることを確認."""
        from src.api.handlers.races import get_race_dates

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
                race_id="2024060201",
                race_name="1R",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 6, 2, 10, 0),
                betting_deadline=datetime(2024, 6, 2, 9, 55),
                track_condition="良",
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {"queryStringParameters": None}

        response = get_race_dates(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["dates"]) == 2
        # 降順で返される
        assert "2024-06-02" in body["dates"]
        assert "2024-06-01" in body["dates"]

    def test_期間指定で開催日をフィルタできる(self) -> None:
        """from/toパラメータで開催日をフィルタできることを確認."""
        from src.api.handlers.races import get_race_dates

        provider = MockRaceDataProvider()
        provider.add_race(
            RaceData(
                race_id="2024053101",
                race_name="1R",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 5, 31, 10, 0),
                betting_deadline=datetime(2024, 5, 31, 9, 55),
                track_condition="良",
            )
        )
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
                race_id="2024060201",
                race_name="1R",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 6, 2, 10, 0),
                betting_deadline=datetime(2024, 6, 2, 9, 55),
                track_condition="良",
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "queryStringParameters": {"from": "2024-06-01", "to": "2024-06-02"}
        }

        response = get_race_dates(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["dates"]) == 2
        assert "2024-06-01" in body["dates"]
        assert "2024-06-02" in body["dates"]
        # 範囲外の日付は含まれない
        assert "2024-05-31" not in body["dates"]

    def test_不正な日付形式でエラー(self) -> None:
        """不正な日付形式でエラーになることを確認."""
        from src.api.handlers.races import get_race_dates

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"queryStringParameters": {"from": "invalid-date"}}

        response = get_race_dates(event, None)

        assert response["statusCode"] == 400
