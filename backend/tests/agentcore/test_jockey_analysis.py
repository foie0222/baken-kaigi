"""騎手分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.jockey_analysis import analyze_jockey_factor
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeJockeyFactor:
    """騎手分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_jockey")
    def test_正常系_騎手を分析(self, mock_get_jockey, mock_get_performances):
        """正常系: 騎手データを正しく分析できる."""
        mock_get_jockey.return_value = {
            "jockey_id": "jockey_001",
            "jockey_name": "テスト騎手",
            "stats": {"win_rate": 18.5, "place_rate": 45.0},
            "by_venue": [],
            "by_track_type": [],
            "by_popularity": [],
        }
        mock_get_performances.return_value = []

        result = analyze_jockey_factor(
            jockey_id="jockey_001",
            jockey_name="テスト騎手",
            horse_id="horse_001",
            horse_name="テスト馬",
            track_type="芝",
            distance=1600,
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["jockey_name"] == "テスト騎手"
        assert "jockey_overview" in result
        assert "course_performance" in result
        assert "horse_compatibility" in result

    @patch("tools.dynamodb_client.get_jockey")
    def test_騎手データなしで警告を返す(self, mock_get_jockey):
        """異常系: 騎手データがない場合はwarningを返す."""
        mock_get_jockey.return_value = None

        result = analyze_jockey_factor(
            jockey_id="jockey_999",
            jockey_name="不明騎手",
        )

        assert "warning" in result

    @patch("tools.dynamodb_client.get_jockey")
    def test_DynamoDB例外時にエラーを返す(self, mock_get_jockey):
        """異常系: DynamoDB例外発生時はerrorを返す."""
        mock_get_jockey.side_effect = Exception("Connection failed")

        result = analyze_jockey_factor(
            jockey_id="jockey_001",
            jockey_name="テスト騎手",
        )

        assert "error" in result
