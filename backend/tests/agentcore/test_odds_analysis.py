"""オッズ分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.odds_analysis import analyze_odds_movement, _estimate_fair_odds_from_ai
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.odds_analysis.get_api_url", return_value="https://api.example.com"):
        yield


class TestAnalyzeOddsMovement:
    """オッズ分析統合テスト."""

    @patch("tools.odds_analysis.cached_get")
    def test_正常系_オッズを分析(self, mock_get):
        """正常系: オッズデータを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "odds_history": [
                {
                    "timestamp": "10:00",
                    "odds": [
                        {"horse_number": 1, "horse_name": "馬1", "odds": 5.5, "popularity": 1},
                    ],
                    "total_pool": 1000000,
                },
                {
                    "timestamp": "11:00",
                    "odds": [
                        {"horse_number": 1, "horse_name": "馬1", "odds": 4.5, "popularity": 1},
                    ],
                    "total_pool": 2000000,
                },
            ],
        }
        mock_get.return_value = mock_response

        result = analyze_odds_movement(
            race_id="202601250611",
            horse_numbers=[1],
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.odds_analysis.cached_get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_odds_movement(
            race_id="202601250611",
            horse_numbers=[1],
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
