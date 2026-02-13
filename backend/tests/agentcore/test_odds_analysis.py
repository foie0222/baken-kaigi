"""オッズ分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.odds_analysis import analyze_odds_movement, _estimate_fair_odds_from_ai
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


def _make_odds_history():
    """テスト用オッズ履歴データ."""
    return [
        {
            "timestamp": "2026-01-25T10:00:00",
            "odds": [
                {"horse_number": 1, "horse_name": "テスト馬A", "odds": 3.5},
                {"horse_number": 2, "horse_name": "テスト馬B", "odds": 5.0},
                {"horse_number": 3, "horse_name": "テスト馬C", "odds": 10.0},
            ],
        },
        {
            "timestamp": "2026-01-25T11:00:00",
            "odds": [
                {"horse_number": 1, "horse_name": "テスト馬A", "odds": 2.5},
                {"horse_number": 2, "horse_name": "テスト馬B", "odds": 8.0},
                {"horse_number": 3, "horse_name": "テスト馬C", "odds": 9.0},
            ],
        },
        {
            "timestamp": "2026-01-25T12:00:00",
            "odds": [
                {"horse_number": 1, "horse_name": "テスト馬A", "odds": 2.0},
                {"horse_number": 2, "horse_name": "テスト馬B", "odds": 12.0},
                {"horse_number": 3, "horse_name": "テスト馬C", "odds": 8.0},
            ],
        },
    ]


class TestAnalyzeOddsMovement:
    """オッズ分析統合テスト."""

    @patch("tools.odds_client.get_win_odds")
    @patch("tools.odds_client.get_odds_history")
    def test_正常系_オッズを分析(self, mock_history, mock_win_odds):
        """正常系: オッズ履歴データがある場合、分析結果を返す."""
        mock_history.return_value = _make_odds_history()
        mock_win_odds.return_value = []

        result = analyze_odds_movement(
            race_id="20260125_06_11",
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["race_id"] == "20260125_06_11"
        assert "market_overview" in result
        assert "movements" in result

    @patch("tools.odds_client.get_odds_history")
    def test_オッズ履歴なしで警告を返す(self, mock_history):
        """オッズ履歴が空の場合、警告を返す."""
        mock_history.return_value = []

        result = analyze_odds_movement(
            race_id="20260125_06_11",
        )

        assert "warning" in result
        assert result["race_id"] == "20260125_06_11"

    @patch("tools.odds_client.get_odds_history")
    def test_例外時にエラーを返す(self, mock_history):
        """異常系: Exception発生時はerrorを返す."""
        mock_history.side_effect = Exception("API error")

        result = analyze_odds_movement(
            race_id="20260125_06_11",
        )

        assert "error" in result


class TestEstimateFairOddsFromAi:
    """AI指数からフェアオッズ推定のテスト（対数線形補間）."""

    def test_AIスコア350は2倍と3倍の間(self):
        odds = _estimate_fair_odds_from_ai(350, 1)
        assert 2.0 < odds < 3.0

    def test_AIスコア400以上は2倍(self):
        odds = _estimate_fair_odds_from_ai(400, 1)
        assert odds == 2.0
        odds_over = _estimate_fair_odds_from_ai(500, 1)
        assert odds_over == 2.0

    def test_AIスコア0以下は順位フォールバック(self):
        odds = _estimate_fair_odds_from_ai(0, 3)
        assert odds == 8.0  # rank 3 → 8.0
        odds_neg = _estimate_fair_odds_from_ai(-10, 5)
        assert odds_neg == 18.0  # rank 5 → 18.0

    def test_AIスコア175は5倍と8倍の間(self):
        odds = _estimate_fair_odds_from_ai(175, 4)
        assert 5.0 < odds < 8.0

    def test_アンカー点は正確な値を返す(self):
        assert _estimate_fair_odds_from_ai(300, 2) == 3.0
        assert _estimate_fair_odds_from_ai(200, 3) == 5.0
        assert _estimate_fair_odds_from_ai(100, 6) == 15.0
        assert _estimate_fair_odds_from_ai(50, 8) == 30.0
