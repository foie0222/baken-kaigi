"""総合レース分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.race_comprehensive_analysis import analyze_race_comprehensive
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.race_comprehensive_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.race_comprehensive_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeRaceComprehensive:
    """総合レース分析統合テスト."""

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_正常系_レースを総合分析(self, mock_get):
        """正常系: レースデータを総合的に分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "race": {
                "race_name": "テストレース",
                "distance": 1600,
                "track_type": "芝",
            },
            "runners": [
                {"horse_number": 1, "horse_name": "馬1", "odds": 2.5},
                {"horse_number": 2, "horse_name": "馬2", "odds": 5.0},
            ],
        }
        mock_get.return_value = mock_response

        result = analyze_race_comprehensive(race_id="20260125_06_11")

        assert "error" not in result or "warning" in result

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_race_comprehensive(race_id="20260125_06_11")

        assert "error" in result
