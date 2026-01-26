"""馬主・生産者API ハンドラーテスト."""
from unittest.mock import MagicMock

import pytest

from src.api.handlers.owners import (
    get_breeder_info,
    get_breeder_stats,
    get_owner_info,
    get_owner_stats,
)
from src.domain.ports import BreederInfoData, BreederStatsData, OwnerInfoData, OwnerStatsData


@pytest.fixture
def mock_provider(monkeypatch):
    """モックプロバイダーをセットアップする."""
    mock = MagicMock()
    monkeypatch.setattr(
        "src.api.handlers.owners.Dependencies.get_race_data_provider",
        lambda: mock,
    )
    return mock


class TestGetOwnerInfo:
    """get_owner_info ハンドラーのテスト."""

    def test_owner_idがない場合は400を返す(self, mock_provider):
        """owner_idがない場合は400エラーを返す."""
        event = {"pathParameters": {}}
        result = get_owner_info(event, None)
        assert result["statusCode"] == 400

    def test_馬主が見つからない場合は404を返す(self, mock_provider):
        """馬主が見つからない場合は404を返す."""
        mock_provider.get_owner_info.return_value = None
        event = {"pathParameters": {"owner_id": "000001"}}
        result = get_owner_info(event, None)
        assert result["statusCode"] == 404

    def test_正常な馬主情報を返す(self, mock_provider):
        """正常な馬主情報を返す."""
        mock_provider.get_owner_info.return_value = OwnerInfoData(
            owner_id="000001",
            owner_name="テスト馬主",
            representative_name="代表太郎",
            registered_year=2000,
        )

        event = {"pathParameters": {"owner_id": "000001"}}
        result = get_owner_info(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert body["owner_id"] == "000001"
        assert body["owner_name"] == "テスト馬主"
        assert body["representative_name"] == "代表太郎"
        assert body["registered_year"] == 2000


class TestGetOwnerStats:
    """get_owner_stats ハンドラーのテスト."""

    def test_owner_idがない場合は400を返す(self, mock_provider):
        """owner_idがない場合は400エラーを返す."""
        event = {"pathParameters": {}, "queryStringParameters": None}
        result = get_owner_stats(event, None)
        assert result["statusCode"] == 400

    def test_不正なyear形式は400を返す(self, mock_provider):
        """yearが不正な形式の場合は400を返す."""
        event = {
            "pathParameters": {"owner_id": "000001"},
            "queryStringParameters": {"year": "invalid"},
        }
        result = get_owner_stats(event, None)
        assert result["statusCode"] == 400

    def test_不正なperiodは400を返す(self, mock_provider):
        """periodが不正な場合は400を返す."""
        event = {
            "pathParameters": {"owner_id": "000001"},
            "queryStringParameters": {"period": "invalid"},
        }
        result = get_owner_stats(event, None)
        assert result["statusCode"] == 400

    def test_統計が見つからない場合は404を返す(self, mock_provider):
        """馬主統計が見つからない場合は404を返す."""
        mock_provider.get_owner_stats.return_value = None
        event = {
            "pathParameters": {"owner_id": "000001"},
            "queryStringParameters": None,
        }
        result = get_owner_stats(event, None)
        assert result["statusCode"] == 404

    def test_正常な馬主統計を返す(self, mock_provider):
        """正常な馬主統計を返す."""
        mock_provider.get_owner_stats.return_value = OwnerStatsData(
            owner_id="000001",
            owner_name="テスト馬主",
            total_horses=50,
            total_starts=500,
            wins=80,
            second_places=60,
            third_places=50,
            win_rate=16.0,
            place_rate=38.0,
            total_prize=1000000000,
            g1_wins=5,
            period="all",
            year=None,
        )

        event = {
            "pathParameters": {"owner_id": "000001"},
            "queryStringParameters": None,
        }
        result = get_owner_stats(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert body["owner_id"] == "000001"
        assert body["total_horses"] == 50
        assert body["wins"] == 80
        assert body["g1_wins"] == 5


class TestGetBreederInfo:
    """get_breeder_info ハンドラーのテスト."""

    def test_breeder_idがない場合は400を返す(self, mock_provider):
        """breeder_idがない場合は400エラーを返す."""
        event = {"pathParameters": {}}
        result = get_breeder_info(event, None)
        assert result["statusCode"] == 400

    def test_生産者が見つからない場合は404を返す(self, mock_provider):
        """生産者が見つからない場合は404を返す."""
        mock_provider.get_breeder_info.return_value = None
        event = {"pathParameters": {"breeder_id": "000001"}}
        result = get_breeder_info(event, None)
        assert result["statusCode"] == 404

    def test_正常な生産者情報を返す(self, mock_provider):
        """正常な生産者情報を返す."""
        mock_provider.get_breeder_info.return_value = BreederInfoData(
            breeder_id="000001",
            breeder_name="テスト牧場",
            location="北海道日高郡",
            registered_year=1980,
        )

        event = {"pathParameters": {"breeder_id": "000001"}}
        result = get_breeder_info(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert body["breeder_id"] == "000001"
        assert body["breeder_name"] == "テスト牧場"
        assert body["location"] == "北海道日高郡"


class TestGetBreederStats:
    """get_breeder_stats ハンドラーのテスト."""

    def test_breeder_idがない場合は400を返す(self, mock_provider):
        """breeder_idがない場合は400エラーを返す."""
        event = {"pathParameters": {}, "queryStringParameters": None}
        result = get_breeder_stats(event, None)
        assert result["statusCode"] == 400

    def test_不正なyear形式は400を返す(self, mock_provider):
        """yearが不正な形式の場合は400を返す."""
        event = {
            "pathParameters": {"breeder_id": "000001"},
            "queryStringParameters": {"year": "invalid"},
        }
        result = get_breeder_stats(event, None)
        assert result["statusCode"] == 400

    def test_統計が見つからない場合は404を返す(self, mock_provider):
        """生産者統計が見つからない場合は404を返す."""
        mock_provider.get_breeder_stats.return_value = None
        event = {
            "pathParameters": {"breeder_id": "000001"},
            "queryStringParameters": None,
        }
        result = get_breeder_stats(event, None)
        assert result["statusCode"] == 404

    def test_正常な生産者統計を返す(self, mock_provider):
        """正常な生産者統計を返す."""
        mock_provider.get_breeder_stats.return_value = BreederStatsData(
            breeder_id="000001",
            breeder_name="テスト牧場",
            total_horses=200,
            total_starts=2000,
            wins=300,
            second_places=250,
            third_places=200,
            win_rate=15.0,
            place_rate=37.5,
            total_prize=5000000000,
            g1_wins=10,
            period="all",
            year=None,
        )

        event = {
            "pathParameters": {"breeder_id": "000001"},
            "queryStringParameters": None,
        }
        result = get_breeder_stats(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert body["breeder_id"] == "000001"
        assert body["breeder_name"] == "テスト牧場"
        assert body["total_horses"] == 200
        assert body["g1_wins"] == 10

    def test_yearパラメータで年指定統計を取得(self, mock_provider):
        """年指定で統計を取得する."""
        mock_provider.get_breeder_stats.return_value = BreederStatsData(
            breeder_id="000001",
            breeder_name="テスト牧場",
            total_horses=20,
            total_starts=200,
            wins=30,
            second_places=25,
            third_places=20,
            win_rate=15.0,
            place_rate=37.5,
            total_prize=500000000,
            g1_wins=1,
            period="all",
            year=2024,
        )

        event = {
            "pathParameters": {"breeder_id": "000001"},
            "queryStringParameters": {"year": "2024"},
        }
        result = get_breeder_stats(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert body["year"] == 2024
        mock_provider.get_breeder_stats.assert_called_once_with(
            "000001", year=2024, period="all"
        )
