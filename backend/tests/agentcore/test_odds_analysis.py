"""オッズ分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.odds_analysis import analyze_odds_movement
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.odds_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.odds_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeOddsMovement:
    """オッズ分析統合テスト."""

    @patch("tools.odds_analysis.requests.get")
    def test_正常系_オッズを分析(self, mock_get):
        """正常系: オッズデータを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "odds_history": [
                {
                    "timestamp": "10:00",
                    "odds": [
                        {"horse_number": 1, "horse_name": "馬1", "odds": 5.5, "popularity": 1},
                    ],
                    "total_pool": 1000000,
                },
                {
                    "timestamp": "11:00",
                    "odds": [
                        {"horse_number": 1, "horse_name": "馬1", "odds": 4.5, "popularity": 1},
                    ],
                    "total_pool": 2000000,
                },
            ],
        }
        mock_get.return_value = mock_response

        result = analyze_odds_movement(
            race_id="20260125_06_11",
            horse_numbers=[1],
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.odds_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_odds_movement(
            race_id="20260125_06_11",
            horse_numbers=[1],
        )

        assert "error" in result
