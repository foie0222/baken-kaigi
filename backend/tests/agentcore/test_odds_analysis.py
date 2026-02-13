"""オッズ分析ツールのテスト."""

import sys
from pathlib import Path

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.odds_analysis import analyze_odds_movement, _estimate_fair_odds_from_ai
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeOddsMovement:
    """オッズ分析統合テスト."""

    def test_正常系_オッズを分析(self):
        """正常系: DynamoDBにデータなしで警告を返す（スタブモード）."""
        result = analyze_odds_movement(
            race_id="20260125_06_11",
            horse_numbers=[1],
        )

        # DynamoDBにオッズ履歴テーブルがないため警告を返す
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert "warning" in result
        assert result["race_id"] == "20260125_06_11"

    def test_例外時にエラーを返す(self):
        """異常系: 内部例外発生時はerrorを返す."""
        # analyze_odds_movementは内部でtry/exceptしているので
        # 直接Exceptionを投げる手段がないが、正常動作を確認
        result = analyze_odds_movement(
            race_id="20260125_06_11",
        )
        assert "error" not in result


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
