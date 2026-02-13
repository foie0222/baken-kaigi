"""馬場状態分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.track_condition_analysis import analyze_track_condition_impact
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeTrackConditionImpact:
    """馬場状態分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_race")
    def test_正常系_馬場状態を分析(self, mock_get_race, mock_get_perfs):
        """正常系: 馬場状態を正しく分析できる."""
        mock_get_race.return_value = {
            "track_condition": "重",
            "track_type": "芝",
            "distance": 1600,
        }
        mock_get_perfs.return_value = [
            {"track_condition": "重", "finish_position": 1, "running_style": "先行"},
            {"track_condition": "良", "finish_position": 3, "running_style": "先行"},
        ]

        result = analyze_track_condition_impact(
            race_id="20260125_06_11",
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.dynamodb_client.get_race")
    def test_例外時にエラーを返す(self, mock_get_race):
        """異常系: 例外発生時はerrorを返す."""
        mock_get_race.side_effect = Exception("Connection failed")

        result = analyze_track_condition_impact(
            race_id="20260125_06_11",
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" in result
