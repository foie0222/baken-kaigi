"""買い目確率分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.bet_probability_analysis import analyze_bet_probability
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeBetProbability:
    """買い目確率分析統合テスト."""

    @patch("tools.dynamodb_client.get_race")
    def test_正常系_買い目確率を分析(self, mock_get_race):
        """正常系: 買い目確率を正しく分析できる.

        NOTE: _get_past_statistics は統計テーブル未整備のためNoneを返す。
        そのため warning が返される。
        """
        mock_get_race.return_value = {
            "race_name": "テストレース",
            "distance": 1600,
            "track_type": "芝",
        }

        result = analyze_bet_probability(
            race_id="20260125_06_11",
            bet_type="単勝",
            analysis_scope="条件別",
        )

        # 統計データ未整備のためwarningが返る
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert "warning" in result

    @patch("tools.dynamodb_client.get_race")
    def test_例外時にエラーを返す(self, mock_get_race):
        """異常系: 例外発生時はerrorを返す."""
        mock_get_race.side_effect = Exception("Connection failed")

        result = analyze_bet_probability(
            race_id="20260125_06_11",
            bet_type="単勝",
        )

        assert "error" in result
