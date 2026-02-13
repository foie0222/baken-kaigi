"""前走分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.last_race_analysis import analyze_last_race_detail
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeLastRaceDetail:
    """前走分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_race")
    def test_正常系_前走を分析(self, mock_get_race, mock_get_perfs):
        """正常系: 前走データを正しく分析できる."""
        mock_get_race.return_value = {
            "race_name": "今回のレース",
            "distance": 1600,
            "track_type": "芝",
            "track_condition": "良",
            "grade_class": "3勝",
            "venue": "東京",
        }
        mock_get_perfs.return_value = [
            {
                "race_name": "前走レース",
                "finish_position": 2,
                "margin": "クビ",
                "distance": 1600,
                "track_type": "芝",
                "track_condition": "良",
                "venue": "東京",
                "race_date": "2026-01-10",
                "last_3f": "33.8",
                "time": "1:33.5",
                "popularity": 2,
                "odds": 5.0,
                "grade_class": "3勝",
                "total_runners": 16,
            },
        ]

        result = analyze_last_race_detail(
            horse_id="horse_001",
            horse_name="テスト馬",
            race_id="20260125_06_11",
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.dynamodb_client.get_race")
    def test_例外時にエラーを返す(self, mock_get_race):
        """異常系: 例外発生時はerrorを返す."""
        mock_get_race.side_effect = Exception("Connection failed")

        result = analyze_last_race_detail(
            horse_id="horse_001",
            horse_name="テスト馬",
            race_id="20260125_06_11",
        )

        assert "error" in result
