"""タイム分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.time_analysis import analyze_time_performance
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeTimePerformance:
    """タイム分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_race")
    def test_正常系_タイムを分析(self, mock_get_race, mock_get_perfs):
        """正常系: タイムを正しく分析できる."""
        mock_get_race.return_value = {
            "distance": 1600,
            "track_type": "芝",
            "track_condition": "良",
        }
        mock_get_perfs.return_value = [
            {
                "distance": 1600,
                "time": "1:33.5",
                "last_3f": "34.0",
                "track_condition": "良",
                "race_name": "テストレース",
                "race_date": "2026-01-01",
            },
        ]

        result = analyze_time_performance(
            horse_id="horse_001",
            horse_name="テスト馬",
            race_id="20260125_06_11",
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_例外時にwarningまたはerrorが返る(self, mock_get_perfs):
        """異常系: 例外発生時はwarningまたはerrorで処理される."""
        mock_get_perfs.side_effect = Exception("Connection failed")

        result = analyze_time_performance(
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        has_warning = "warning" in result
        has_error = "error" in result
        assert has_warning or has_error, "Expected either 'warning' or 'error' key in result"
