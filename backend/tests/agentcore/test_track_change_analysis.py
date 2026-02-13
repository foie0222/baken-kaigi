"""馬場変更分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.track_change_analysis import track_course_condition_change
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_dynamodb_client():
    """DynamoDBクライアントをモック化."""
    with patch("tools.track_change_analysis.dynamodb_client") as mock_client:
        mock_client.get_race.return_value = {}
        yield mock_client


class TestTrackCourseConditionChange:
    """馬場変更分析統合テスト."""

    def test_正常系_馬場変更を分析(self, mock_dynamodb_client):
        """正常系: 馬場変更を正しく分析できる."""
        mock_dynamodb_client.get_race.return_value = {
            "race_name": "テストレース",
            "track_condition": "重",
            "track_type": "芝",
            "venue": "東京",
            "distance": 1600,
            "race_number": 11,
            "race_date": "2026-01-25",
        }

        result = track_course_condition_change(
            race_id="20260125_06_11",
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    def test_Exception時にエラーを返す(self, mock_dynamodb_client):
        """異常系: Exception発生時はerrorを返す."""
        mock_dynamodb_client.get_race.side_effect = Exception("Connection failed")

        result = track_course_condition_change(
            race_id="20260125_06_11",
        )

        assert "error" in result
