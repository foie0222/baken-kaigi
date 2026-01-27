"""買い目確率分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.bet_probability_analysis import analyze_bet_probability
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.bet_probability_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.bet_probability_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeBetProbability:
    """買い目確率分析統合テスト."""

    @patch("tools.bet_probability_analysis.requests.get")
    def test_正常系_買い目確率を分析(self, mock_get):
        """正常系: 買い目確率を正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "runners": [
                {"horse_number": 1, "odds": 2.5, "popularity": 1},
                {"horse_number": 2, "odds": 5.0, "popularity": 2},
            ],
        }
        mock_get.return_value = mock_response

        result = analyze_bet_probability(
            race_id="20260125_06_11",
            bet_type="trio",
            horse_numbers=[1, 2, 3],
        )

        assert "error" not in result or "warning" in result

    @patch("tools.bet_probability_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_bet_probability(
            race_id="20260125_06_11",
            bet_type="win",
            horse_numbers=[1],
        )

        assert "error" in result
