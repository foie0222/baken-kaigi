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
    with patch("tools.distance_change_analysis.get_api_url", return_value="https://api.example.com"):
        yield


class TestAnalyzeDistanceChange:
    """距離変更分析統合テスト."""

    @patch("tools.distance_change_analysis.cached_get")
    def test_正常系_距離変更を分析(self, mock_get):
        """正常系: 距離変更を正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "distance": 2000,
            "track_type": "芝",
            "performances": [
                {"distance": 1600, "finish_position": 1},
                {"distance": 1800, "finish_position": 2},
            ],
        }
        mock_get.return_value = mock_response

        result = analyze_distance_change(
            race_id="20260125_06_11",
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.distance_change_analysis.cached_get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_distance_change(
            race_id="20260125_06_11",
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" in result
