"""馬券組み合わせツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.bet_combinations import suggest_bet_combinations
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.bet_combinations.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.bet_combinations.get_api_url", return_value="https://api.example.com"):
            yield


class TestSuggestBetCombinations:
    """馬券組み合わせ統合テスト."""

    @patch("tools.bet_combinations.requests.get")
    def test_正常系_馬券組み合わせを提案(self, mock_get):
        """正常系: 馬券組み合わせを正しく提案できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "runners": [
                {"horse_number": 1, "odds": 2.5, "popularity": 1},
                {"horse_number": 2, "odds": 5.0, "popularity": 2},
                {"horse_number": 3, "odds": 10.0, "popularity": 3},
            ],
        }
        mock_get.return_value = mock_response

        result = suggest_bet_combinations(
            race_id="20260125_06_11",
            axis_horses=[1],
            bet_type="馬連",
            budget=1000,
        )

        assert "error" not in result or "warning" in result

    @patch("tools.bet_combinations.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = suggest_bet_combinations(
            race_id="20260125_06_11",
            axis_horses=[1],
            bet_type="馬連",
            budget=1000,
        )

        assert "error" in result
