"""馬体重分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.weight_analysis import analyze_weight_trend
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeWeightTrend:
    """馬体重分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_正常系_馬体重を分析(self, mock_get_perfs):
        """正常系: 馬体重データを正しく分析できる."""
        mock_get_perfs.return_value = [
            {
                "race_date": "20260120",
                "horse_weight": 480,
                "finish_position": 2,
                "race_name": "テストレース1",
            },
            {
                "race_date": "20251215",
                "horse_weight": 478,
                "finish_position": 3,
                "race_name": "テストレース2",
            },
        ]

        result = analyze_weight_trend(
            horse_id="horse_001",
            horse_name="テスト馬",
            current_weight=480,
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_例外時にエラーを返す(self, mock_get_perfs):
        """異常系: Exception発生時はerrorを返す."""
        mock_get_perfs.side_effect = Exception("Connection failed")

        result = analyze_weight_trend(
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" in result
