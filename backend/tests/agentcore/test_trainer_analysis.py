"""厩舎（調教師）分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.trainer_analysis import analyze_trainer_tendency
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.trainer_analysis.get_api_url", return_value="https://api.example.com"):
        yield


class TestAnalyzeTrainerTendency:
    """厩舎分析統合テスト."""

    @patch("tools.trainer_analysis.cached_get")
    def test_正常系_厩舎を分析(self, mock_get):
        """正常系: 厩舎データを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trainer_name": "テスト調教師",
            "stable": "栗東",
            "win_rate": 12.5,
            "place_rate": 35.0,
        }
        mock_get.return_value = mock_response

        result = analyze_trainer_tendency(
            "trainer_001", "テスト調教師",
            track_type="芝",
            distance=1600,
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.trainer_analysis.cached_get")
    def test_404エラーで警告を返す(self, mock_get):
        """異常系: 404の場合は警告を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = analyze_trainer_tendency("trainer_999", "不明調教師")

        assert "warning" in result

    @patch("tools.trainer_analysis.cached_get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_trainer_tendency("trainer_001", "テスト調教師")

        assert "error" in result
