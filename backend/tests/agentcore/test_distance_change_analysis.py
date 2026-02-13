"""距離変更分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.distance_change_analysis import analyze_distance_change
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeDistanceChange:
    """距離変更分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_race")
    def test_正常系_距離変更を分析(self, mock_get_race, mock_get_perfs):
        """正常系: 距離変更を正しく分析できる."""
        mock_get_race.return_value = {
            "distance": 2000,
            "track_type": "芝",
        }
        mock_get_perfs.return_value = [
            {"distance": 1600, "finish_position": 1},
            {"distance": 1800, "finish_position": 2},
        ]

        result = analyze_distance_change(
            race_id="20260125_06_11",
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.dynamodb_client.get_race")
    def test_例外時にエラーを返す(self, mock_get_race):
        """異常系: 例外発生時はerrorを返す."""
        mock_get_race.side_effect = Exception("Connection failed")

        result = analyze_distance_change(
            race_id="20260125_06_11",
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" in result
