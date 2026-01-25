"""騎手APIハンドラーのテスト."""
import json

import pytest

from src.api.dependencies import Dependencies
from src.domain.ports import (
    JockeyInfoData,
    JockeyStatsDetailData,
    RaceDataProvider,
)
from tests.api.handlers.test_races import MockRaceDataProvider


class JockeyMockRaceDataProvider(MockRaceDataProvider):
    """騎手テスト用のモックレースデータプロバイダ."""

    def __init__(self) -> None:
        super().__init__()
        self._jockey_info: dict[str, JockeyInfoData] = {}
        self._jockey_stats: dict[str, JockeyStatsDetailData] = {}

    def add_jockey_info(self, info: JockeyInfoData) -> None:
        self._jockey_info[info.jockey_id] = info

    def add_jockey_stats(self, stats: JockeyStatsDetailData) -> None:
        key = f"{stats.jockey_id}_{stats.year}_{stats.period}"
        self._jockey_stats[key] = stats

    def get_jockey_info(self, jockey_id: str) -> JockeyInfoData | None:
        return self._jockey_info.get(jockey_id)

    def get_jockey_stats_detail(
        self,
        jockey_id: str,
        year: int | None = None,
        period: str = "recent",
    ) -> JockeyStatsDetailData | None:
        key = f"{jockey_id}_{year}_{period}"
        return self._jockey_stats.get(key)


@pytest.fixture(autouse=True)
def reset_dependencies():
    """各テスト前に依存性をリセット."""
    Dependencies.reset()
    yield
    Dependencies.reset()


class TestGetJockeyInfoHandler:
    """GET /jockeys/{jockey_id}/info ハンドラーのテスト."""

    def test_騎手基本情報を取得できる(self) -> None:
        """騎手基本情報を取得できることを確認."""
        from src.api.handlers.jockeys import get_jockey_info

        provider = JockeyMockRaceDataProvider()
        provider.add_jockey_info(
            JockeyInfoData(
                jockey_id="01234",
                jockey_name="武豊",
                jockey_name_kana="タケユタカ",
                birth_date="1969-03-15",
                affiliation="栗東",
                license_year=1987,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"jockey_id": "01234"}}

        response = get_jockey_info(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["jockey_id"] == "01234"
        assert body["jockey_name"] == "武豊"
        assert body["jockey_name_kana"] == "タケユタカ"
        assert body["birth_date"] == "1969-03-15"
        assert body["affiliation"] == "栗東"
        assert body["license_year"] == 1987

    def test_存在しない騎手で404(self) -> None:
        """存在しない騎手で404が返ることを確認."""
        from src.api.handlers.jockeys import get_jockey_info

        provider = JockeyMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"jockey_id": "99999"}}

        response = get_jockey_info(event, None)

        assert response["statusCode"] == 404

    def test_騎手IDがないとエラー(self) -> None:
        """騎手IDがないとエラーになることを確認."""
        from src.api.handlers.jockeys import get_jockey_info

        provider = JockeyMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": None}

        response = get_jockey_info(event, None)

        assert response["statusCode"] == 400


class TestGetJockeyStatsHandler:
    """GET /jockeys/{jockey_id}/stats ハンドラーのテスト."""

    def test_騎手成績統計を取得できる(self) -> None:
        """騎手成績統計を取得できることを確認."""
        from src.api.handlers.jockeys import get_jockey_stats

        provider = JockeyMockRaceDataProvider()
        provider.add_jockey_stats(
            JockeyStatsDetailData(
                jockey_id="01234",
                jockey_name="武豊",
                total_rides=500,
                wins=100,
                second_places=80,
                third_places=70,
                win_rate=0.20,
                place_rate=0.50,
                period="recent",
                year=None,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"jockey_id": "01234"},
            "queryStringParameters": None,
        }

        response = get_jockey_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["jockey_id"] == "01234"
        assert body["jockey_name"] == "武豊"
        assert body["total_rides"] == 500
        assert body["wins"] == 100
        assert body["second_places"] == 80
        assert body["third_places"] == 70
        assert body["win_rate"] == 0.20
        assert body["place_rate"] == 0.50
        assert body["period"] == "recent"
        assert body["year"] is None

    def test_年指定で騎手成績統計を取得できる(self) -> None:
        """年指定で騎手成績統計を取得できることを確認."""
        from src.api.handlers.jockeys import get_jockey_stats

        provider = JockeyMockRaceDataProvider()
        provider.add_jockey_stats(
            JockeyStatsDetailData(
                jockey_id="01234",
                jockey_name="武豊",
                total_rides=200,
                wins=40,
                second_places=30,
                third_places=25,
                win_rate=0.20,
                place_rate=0.475,
                period="recent",
                year=2024,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"jockey_id": "01234"},
            "queryStringParameters": {"year": "2024"},
        }

        response = get_jockey_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["year"] == 2024

    def test_period指定で騎手成績統計を取得できる(self) -> None:
        """period指定で騎手成績統計を取得できることを確認."""
        from src.api.handlers.jockeys import get_jockey_stats

        provider = JockeyMockRaceDataProvider()
        provider.add_jockey_stats(
            JockeyStatsDetailData(
                jockey_id="01234",
                jockey_name="武豊",
                total_rides=5000,
                wins=1000,
                second_places=800,
                third_places=700,
                win_rate=0.20,
                place_rate=0.50,
                period="all",
                year=None,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"jockey_id": "01234"},
            "queryStringParameters": {"period": "all"},
        }

        response = get_jockey_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["period"] == "all"

    def test_存在しない騎手で404(self) -> None:
        """存在しない騎手で404が返ることを確認."""
        from src.api.handlers.jockeys import get_jockey_stats

        provider = JockeyMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"jockey_id": "99999"},
            "queryStringParameters": None,
        }

        response = get_jockey_stats(event, None)

        assert response["statusCode"] == 404

    def test_騎手IDがないとエラー(self) -> None:
        """騎手IDがないとエラーになることを確認."""
        from src.api.handlers.jockeys import get_jockey_stats

        provider = JockeyMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": None,
            "queryStringParameters": None,
        }

        response = get_jockey_stats(event, None)

        assert response["statusCode"] == 400

    def test_不正なyearでエラー(self) -> None:
        """不正なyearでエラーになることを確認."""
        from src.api.handlers.jockeys import get_jockey_stats

        provider = JockeyMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"jockey_id": "01234"},
            "queryStringParameters": {"year": "invalid"},
        }

        response = get_jockey_stats(event, None)

        assert response["statusCode"] == 400

    def test_不正なperiodでエラー(self) -> None:
        """不正なperiodでエラーになることを確認."""
        from src.api.handlers.jockeys import get_jockey_stats

        provider = JockeyMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"jockey_id": "01234"},
            "queryStringParameters": {"period": "invalid"},
        }

        response = get_jockey_stats(event, None)

        assert response["statusCode"] == 400

    def test_yearの範囲外でエラー(self) -> None:
        """yearが範囲外でエラーになることを確認."""
        from src.api.handlers.jockeys import get_jockey_stats

        provider = JockeyMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"jockey_id": "01234"},
            "queryStringParameters": {"year": "1800"},
        }

        response = get_jockey_stats(event, None)

        assert response["statusCode"] == 400
