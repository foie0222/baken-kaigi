"""馬体重分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.weight_analysis import analyze_weight_trend
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.weight_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.weight_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeWeightTrend:
    """馬体重分析統合テスト."""

    @patch("tools.weight_analysis.requests.get")
    def test_正常系_馬体重を分析(self, mock_get):
        """正常系: 馬体重データを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "weight_history": [
                {"date": "2026-01-20", "weight": 480, "change": 0},
                {"date": "2025-12-15", "weight": 478, "change": -2},
            ],
            "optimal_weight_range": {"min": 475, "max": 485},
        }
        mock_get.return_value = mock_response

        result = analyze_weight_trend(
            horse_id="horse_001",
            horse_name="テスト馬",
            current_weight=480,
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.weight_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_weight_trend(
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" in result
