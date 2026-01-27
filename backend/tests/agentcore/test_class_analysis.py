"""クラス分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.class_analysis import analyze_class_factor
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.class_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.class_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeClassFactor:
    """クラス分析統合テスト."""

    @patch("tools.class_analysis.requests.get")
    def test_正常系_クラス要因を分析(self, mock_get):
        """正常系: クラス要因を正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "current_class": "3勝",
            "suitable_class": "OP",
        }
        mock_get.return_value = mock_response

        result = analyze_class_factor(
            horse_id="horse_001",
            horse_name="テスト馬",
            race_class="OP",
        )

        assert "error" not in result or "warning" in result

    @patch("tools.class_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_class_factor(
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" in result
