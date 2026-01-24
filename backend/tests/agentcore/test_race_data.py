"""レースデータ取得ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

# strandsモジュールが利用できない場合はスキップ
try:
    # agentcoreモジュールをインポートできるようにパスを追加
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

    from tools.race_data import get_race_data
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_get_headers():
    """全テストで get_headers をモック化してboto3呼び出しを防ぐ."""
    with patch("tools.race_data.get_headers", return_value={"x-api-key": "test-key"}):
        yield


@pytest.fixture(autouse=True)
def mock_get_api_url():
    """全テストで get_api_url をモック化."""
    with patch("tools.race_data.get_api_url", return_value="https://api.example.com"):
        yield


class TestGetRaceData:
    """get_race_data統合テスト."""

    @patch("tools.race_data.requests.get")
    def test_正常なAPI応答でraceとrunnersを返す(self, mock_get):
        """正常系: APIが成功した場合、raceとrunnersを含む辞書を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "race": {
                "race_id": "20260125_06_11",
                "race_name": "テストレース",
                "distance": 1600,
                "track_type": "芝",
            },
            "runners": [
                {"horse_number": 1, "horse_name": "テスト馬1", "odds": 2.5, "popularity": 1},
                {"horse_number": 2, "horse_name": "テスト馬2", "odds": 5.0, "popularity": 2},
            ],
        }
        mock_get.return_value = mock_response

        result = get_race_data("20260125_06_11")

        assert "race" in result
        assert "runners" in result
        assert result["race"]["race_name"] == "テストレース"
        assert result["race"]["distance"] == 1600
        assert len(result["runners"]) == 2
        assert result["runners"][0]["horse_name"] == "テスト馬1"

    @patch("tools.race_data.requests.get")
    def test_空のデータでも空の辞書を返す(self, mock_get):
        """空のレスポンスの場合、空のrace/runnersを返す."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        result = get_race_data("20260125_06_11")

        assert result["race"] == {}
        assert result["runners"] == []

    @patch("tools.race_data.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを含む辞書を返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = get_race_data("20260125_06_11")

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]
        assert "Connection failed" in result["error"]

    @patch("tools.race_data.requests.get")
    def test_タイムアウト時にエラーを返す(self, mock_get):
        """異常系: タイムアウト時はerrorを含む辞書を返す."""
        mock_get.side_effect = requests.Timeout("Request timed out")

        result = get_race_data("20260125_06_11")

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]

    @patch("tools.race_data.requests.get")
    def test_HTTPエラー時にエラーを返す(self, mock_get):
        """異常系: HTTPステータスエラー時はerrorを含む辞書を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response

        result = get_race_data("20260125_06_11")

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]

    @patch("tools.race_data.requests.get")
    def test_正しいURLとヘッダーでAPIを呼び出す(self, mock_get):
        """APIが正しいURL、ヘッダー、タイムアウトで呼び出されることを確認."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"race": {}, "runners": []}
        mock_get.return_value = mock_response

        get_race_data("20260125_06_11")

        mock_get.assert_called_once_with(
            "https://api.example.com/races/20260125_06_11",
            headers={"x-api-key": "test-key"},
            timeout=10,
        )
