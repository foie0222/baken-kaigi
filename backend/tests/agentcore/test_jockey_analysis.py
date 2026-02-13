"""騎手分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.jockey_analysis import analyze_jockey_factor
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.jockey_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.jockey_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeJockeyFactor:
    """騎手分析統合テスト."""

    @patch("tools.jockey_analysis.requests.get")
    def test_正常系_騎手を分析(self, mock_get):
        """正常系: 騎手データを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jockey_name": "テスト騎手",
            "win_rate": 18.5,
            "place_rate": 45.0,
            "recent_form": "好調",
        }
        mock_get.return_value = mock_response

        result = analyze_jockey_factor(
            jockey_id="jockey_001",
            jockey_name="テスト騎手",
            horse_id="horse_001",
            track_type="芝",
            distance=1600,
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.jockey_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_jockey_factor(
            jockey_id="jockey_001",
            jockey_name="テスト騎手",
        )

        assert "error" in result
