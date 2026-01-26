"""厩舎（調教師）APIハンドラーのテスト."""
import json

import pytest

from src.api.dependencies import Dependencies
from src.domain.ports import (
    TrainerClassStatsData,
    TrainerInfoData,
    TrainerStatsDetailData,
    TrainerTrackStatsData,
)
from tests.api.handlers.test_races import MockRaceDataProvider


class TrainerMockRaceDataProvider(MockRaceDataProvider):
    """厩舎テスト用のモックレースデータプロバイダ."""

    def __init__(self) -> None:
        super().__init__()
        self._trainer_info: dict[str, TrainerInfoData] = {}
        self._trainer_stats: dict[str, tuple[
            TrainerStatsDetailData,
            list[TrainerTrackStatsData],
            list[TrainerClassStatsData],
        ]] = {}

    def add_trainer_info(self, info: TrainerInfoData) -> None:
        self._trainer_info[info.trainer_id] = info

    def add_trainer_stats(
        self,
        stats: TrainerStatsDetailData,
        track_stats: list[TrainerTrackStatsData],
        class_stats: list[TrainerClassStatsData],
    ) -> None:
        key = f"{stats.trainer_id}_{stats.year}_{stats.period}"
        self._trainer_stats[key] = (stats, track_stats, class_stats)

    def get_trainer_info(self, trainer_id: str) -> TrainerInfoData | None:
        return self._trainer_info.get(trainer_id)

    def get_trainer_stats_detail(
        self,
        trainer_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> tuple[TrainerStatsDetailData | None, list[TrainerTrackStatsData], list[TrainerClassStatsData]]:
        key = f"{trainer_id}_{year}_{period}"
        result = self._trainer_stats.get(key)
        if result:
            return result
        return None, [], []


@pytest.fixture(autouse=True)
def reset_dependencies():
    """各テスト前に依存性をリセット."""
    Dependencies.reset()
    yield
    Dependencies.reset()


class TestGetTrainerInfoHandler:
    """GET /trainers/{trainer_id}/info ハンドラーのテスト."""

    def test_厩舎基本情報を取得できる(self) -> None:
        """厩舎基本情報を取得できることを確認."""
        from src.api.handlers.trainers import get_trainer_info

        provider = TrainerMockRaceDataProvider()
        provider.add_trainer_info(
            TrainerInfoData(
                trainer_id="01234",
                trainer_name="矢作芳人",
                trainer_name_kana="ヤハギヨシト",
                affiliation="栗東",
                stable_location="栗東トレセン",
                license_year=1993,
                career_wins=1500,
                career_starts=8000,
            )
        )
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"trainer_id": "01234"}}

        response = get_trainer_info(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["trainer_id"] == "01234"
        assert body["trainer_name"] == "矢作芳人"
        assert body["trainer_name_kana"] == "ヤハギヨシト"
        assert body["affiliation"] == "栗東"
        assert body["stable_location"] == "栗東トレセン"
        assert body["license_year"] == 1993
        assert body["career_wins"] == 1500
        assert body["career_starts"] == 8000

    def test_存在しない厩舎で404(self) -> None:
        """存在しない厩舎で404が返ることを確認."""
        from src.api.handlers.trainers import get_trainer_info

        provider = TrainerMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"trainer_id": "99999"}}

        response = get_trainer_info(event, None)

        assert response["statusCode"] == 404

    def test_厩舎IDがないとエラー(self) -> None:
        """厩舎IDがないとエラーになることを確認."""
        from src.api.handlers.trainers import get_trainer_info

        provider = TrainerMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": None}

        response = get_trainer_info(event, None)

        assert response["statusCode"] == 400


class TestGetTrainerStatsHandler:
    """GET /trainers/{trainer_id}/stats ハンドラーのテスト."""

    def test_厩舎成績統計を取得できる(self) -> None:
        """厩舎成績統計を取得できることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        provider.add_trainer_stats(
            TrainerStatsDetailData(
                trainer_id="01234",
                trainer_name="矢作芳人",
                total_starts=500,
                wins=100,
                second_places=80,
                third_places=70,
                win_rate=20.0,
                place_rate=50.0,
                prize_money=5000000000,
                period="all",
                year=None,
            ),
            [
                TrainerTrackStatsData(track_type="芝", starts=300, wins=60, win_rate=20.0),
                TrainerTrackStatsData(track_type="ダート", starts=200, wins=40, win_rate=20.0),
            ],
            [
                TrainerClassStatsData(grade_class="G1", starts=50, wins=10, win_rate=20.0),
                TrainerClassStatsData(grade_class="G2", starts=80, wins=20, win_rate=25.0),
            ],
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "01234"},
            "queryStringParameters": None,
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["trainer_id"] == "01234"
        assert body["trainer_name"] == "矢作芳人"
        assert body["stats"]["total_starts"] == 500
        assert body["stats"]["wins"] == 100
        assert body["stats"]["places"] == 250  # wins + second + third
        assert body["stats"]["win_rate"] == 20.0
        assert body["stats"]["place_rate"] == 50.0
        assert body["stats"]["prize_money"] == 5000000000

    def test_トラック別成績が取得できる(self) -> None:
        """トラック別成績が取得できることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        provider.add_trainer_stats(
            TrainerStatsDetailData(
                trainer_id="01234",
                trainer_name="矢作芳人",
                total_starts=500,
                wins=100,
                second_places=80,
                third_places=70,
                win_rate=20.0,
                place_rate=50.0,
                period="all",
                year=None,
            ),
            [
                TrainerTrackStatsData(track_type="芝", starts=300, wins=60, win_rate=20.0),
                TrainerTrackStatsData(track_type="ダート", starts=200, wins=40, win_rate=20.0),
            ],
            [],
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "01234"},
            "queryStringParameters": None,
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["by_track_type"]) == 2
        assert body["by_track_type"][0]["track_type"] == "芝"
        assert body["by_track_type"][0]["starts"] == 300
        assert body["by_track_type"][0]["wins"] == 60
        assert body["by_track_type"][0]["win_rate"] == 20.0

    def test_クラス別成績が取得できる(self) -> None:
        """クラス別成績が取得できることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        provider.add_trainer_stats(
            TrainerStatsDetailData(
                trainer_id="01234",
                trainer_name="矢作芳人",
                total_starts=500,
                wins=100,
                second_places=80,
                third_places=70,
                win_rate=20.0,
                place_rate=50.0,
                period="all",
                year=None,
            ),
            [],
            [
                TrainerClassStatsData(grade_class="G1", starts=50, wins=10, win_rate=20.0),
                TrainerClassStatsData(grade_class="G2", starts=80, wins=20, win_rate=25.0),
            ],
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "01234"},
            "queryStringParameters": None,
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["by_class"]) == 2
        assert body["by_class"][0]["class"] == "G1"
        assert body["by_class"][0]["starts"] == 50
        assert body["by_class"][0]["wins"] == 10
        assert body["by_class"][0]["win_rate"] == 20.0

    def test_年指定で厩舎成績統計を取得できる(self) -> None:
        """年指定で厩舎成績統計を取得できることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        provider.add_trainer_stats(
            TrainerStatsDetailData(
                trainer_id="01234",
                trainer_name="矢作芳人",
                total_starts=200,
                wins=40,
                second_places=30,
                third_places=25,
                win_rate=20.0,
                place_rate=47.5,
                period="all",
                year=2024,
            ),
            [],
            [],
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "01234"},
            "queryStringParameters": {"year": "2024"},
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["stats"]["total_starts"] == 200

    def test_period指定で厩舎成績統計を取得できる(self) -> None:
        """period指定で厩舎成績統計を取得できることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        provider.add_trainer_stats(
            TrainerStatsDetailData(
                trainer_id="01234",
                trainer_name="矢作芳人",
                total_starts=100,
                wins=20,
                second_places=15,
                third_places=10,
                win_rate=20.0,
                place_rate=45.0,
                period="recent",
                year=None,
            ),
            [],
            [],
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "01234"},
            "queryStringParameters": {"period": "recent"},
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["stats"]["total_starts"] == 100

    def test_存在しない厩舎で404(self) -> None:
        """存在しない厩舎で404が返ることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "99999"},
            "queryStringParameters": None,
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 404

    def test_厩舎IDがないとエラー(self) -> None:
        """厩舎IDがないとエラーになることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": None,
            "queryStringParameters": None,
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 400

    def test_不正なyearでエラー(self) -> None:
        """不正なyearでエラーになることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "01234"},
            "queryStringParameters": {"year": "invalid"},
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 400

    def test_不正なperiodでエラー(self) -> None:
        """不正なperiodでエラーになることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "01234"},
            "queryStringParameters": {"period": "invalid"},
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 400

    def test_yearの範囲外でエラー(self) -> None:
        """yearが範囲外でエラーになることを確認."""
        from src.api.handlers.trainers import get_trainer_stats

        provider = TrainerMockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"trainer_id": "01234"},
            "queryStringParameters": {"year": "1800"},
        }

        response = get_trainer_stats(event, None)

        assert response["statusCode"] == 400
