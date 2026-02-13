"""勢い分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.momentum_analysis import analyze_momentum
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeMomentum:
    """勢い分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_正常系_勢いを分析(self, mock_get_perfs):
        """正常系: 勢いを正しく分析できる."""
        mock_get_perfs.return_value = [
            {"finish_position": 1},
            {"finish_position": 2},
            {"finish_position": 3},
        ]

        result = analyze_momentum(
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_例外時にwarningを返す(self, mock_get_perfs):
        """異常系: Exception発生時はwarningを返す（_get_performancesがキャッチ）."""
        mock_get_perfs.side_effect = Exception("Connection failed")

        result = analyze_momentum(
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        # _get_performancesがexceptionをキャッチして空リストを返すので、warningになる
        has_warning = "warning" in result
        has_error = "error" in result
        assert has_warning or has_error, "Expected 'warning' or 'error' on Exception"
