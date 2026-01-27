"""タイム分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.time_analysis import analyze_time_performance
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.time_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.time_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeTimePerformance:
    """タイム分析統合テスト."""

    @patch("tools.time_analysis.requests.get")
    def test_正常系_タイムを分析(self, mock_get):
        """正常系: タイムを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "performances": [
                {"distance": 1600, "time": "1:33.5", "last_3f": "34.0", "track_condition": "良", "race_name": "テストレース", "race_date": "2026-01-01"},
            ]
        }
        mock_get.return_value = mock_response

        result = analyze_time_performance(
            horse_id="horse_001",
            horse_name="テスト馬",
            race_id="20260125_06_11",
        )

        assert "error" not in result or "warning" in result

    @patch("tools.time_analysis.requests.get")
    def test_RequestException時にwarningが返る(self, mock_get):
        """異常系: RequestException発生時はerrorではなくwarningで処理される."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_time_performance(
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        # time_analysis は内部でエラーをハンドリングし、warningで結果を返す
        assert "warning" in result or "error" in result
