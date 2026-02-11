"""馬場変更分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.track_change_analysis import track_course_condition_change
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.track_change_analysis.get_api_url", return_value="https://api.example.com"):
        yield


class TestTrackCourseConditionChange:
    """馬場変更分析統合テスト."""

    @patch("tools.track_change_analysis.cached_get")
    def test_正常系_馬場変更を分析(self, mock_get):
        """正常系: 馬場変更を正しく分析できる."""
        # 1回目: レース情報取得
        mock_race_response = MagicMock()
        mock_race_response.status_code = 200
        mock_race_response.json.return_value = {
            "race_name": "テストレース",
            "track_condition": "重",
            "track_type": "芝",
            "venue": "東京",
            "distance": 1600,
            "race_number": 11,
            "race_date": "2026-01-25",
        }
        mock_race_response.raise_for_status = MagicMock()

        # 2回目: 当日レース情報取得
        mock_daily_response = MagicMock()
        mock_daily_response.status_code = 200
        mock_daily_response.json.return_value = [
            {"race_number": 1, "track_type": "芝", "track_condition": "良"},
            {"race_number": 5, "track_type": "芝", "track_condition": "稍重"},
            {"race_number": 9, "track_type": "芝", "track_condition": "重"},
        ]

        mock_get.side_effect = [mock_race_response, mock_daily_response]

        result = track_course_condition_change(
            race_id="20260125_06_11",
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.track_change_analysis.cached_get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = track_course_condition_change(
            race_id="20260125_06_11",
        )

        assert "error" in result
