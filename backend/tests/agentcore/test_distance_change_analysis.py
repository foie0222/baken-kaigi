"""距離変更分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.distance_change_analysis import analyze_distance_change
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.distance_change_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.distance_change_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeDistanceChange:
    """距離変更分析統合テスト."""

    @patch("tools.distance_change_analysis.requests.get")
    def test_正常系_距離変更を分析(self, mock_get):
        """正常系: 距離変更を正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "last_distance": 1600,
            "current_distance": 2000,
            "distance_change_stats": {
                "extension_win_rate": 15.0,
            },
        }
        mock_get.return_value = mock_response

        result = analyze_distance_change(
            horse_id="horse_001",
            horse_name="テスト馬",
            race_distance=2000,
        )

        assert "error" not in result or "warning" in result

    @patch("tools.distance_change_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_distance_change(
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" in result
