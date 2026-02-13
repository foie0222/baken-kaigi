"""クラス分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.class_analysis import analyze_class_factor
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeClassFactor:
    """クラス分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_race")
    def test_正常系_クラス要因を分析(self, mock_get_race, mock_get_perfs):
        """正常系: クラス要因を正しく分析できる."""
        mock_get_race.return_value = {
            "grade_class": "OP",
            "distance": 1600,
            "track_type": "芝",
        }
        mock_get_perfs.return_value = [
            {"grade_class": "3勝", "finish_position": 1},
            {"grade_class": "3勝", "finish_position": 2},
        ]

        result = analyze_class_factor(
            race_id="20260125_06_11",
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.dynamodb_client.get_race")
    def test_例外時にエラーを返す(self, mock_get_race):
        """異常系: 例外発生時はerrorを返す."""
        mock_get_race.side_effect = Exception("Connection failed")

        result = analyze_class_factor(
            race_id="20260125_06_11",
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" in result
