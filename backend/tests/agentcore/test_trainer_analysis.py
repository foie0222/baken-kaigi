"""厩舎（調教師）分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.trainer_analysis import analyze_trainer_tendency
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeTrainerTendency:
    """厩舎分析統合テスト."""

    @patch("tools.dynamodb_client.get_jockey")
    @patch("tools.dynamodb_client.get_trainer")
    def test_正常系_厩舎を分析(self, mock_get_trainer, mock_get_jockey):
        """正常系: 厩舎データを正しく分析できる."""
        mock_get_trainer.return_value = {
            "trainer_id": "trainer_001",
            "trainer_name": "テスト調教師",
            "affiliation": "栗東",
            "stats": {"win_rate": 12.5, "place_rate": 35.0},
            "by_track_type": [],
            "by_class": [],
        }
        mock_get_jockey.return_value = None

        result = analyze_trainer_tendency(
            "trainer_001", "テスト調教師",
            track_type="芝",
            distance=1600,
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["trainer_name"] == "テスト調教師"
        assert "stable_overview" in result
        assert "race_condition_fit" in result
        assert "jockey_compatibility" in result

    @patch("tools.dynamodb_client.get_trainer")
    def test_調教師データなしで警告を返す(self, mock_get_trainer):
        """異常系: 調教師データがない場合はwarningを返す."""
        mock_get_trainer.return_value = None

        result = analyze_trainer_tendency("trainer_999", "不明調教師")

        assert "warning" in result

    @patch("tools.dynamodb_client.get_trainer")
    def test_DynamoDB例外時にエラーを返す(self, mock_get_trainer):
        """異常系: DynamoDB例外発生時はerrorを返す."""
        mock_get_trainer.side_effect = Exception("Connection failed")

        result = analyze_trainer_tendency("trainer_001", "テスト調教師")

        assert "error" in result
