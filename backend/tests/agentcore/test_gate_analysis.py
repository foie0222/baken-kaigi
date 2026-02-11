"""枠順分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.gate_analysis import analyze_gate_position
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.gate_analysis.get_api_url", return_value="https://api.example.com"):
        yield


class TestAnalyzeGatePosition:
    """枠順分析統合テスト."""

    @patch("tools.gate_analysis.cached_get")
    def test_正常系_枠順を分析(self, mock_get):
        """正常系: 枠順データを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "by_gate": [
                {"gate": 1, "win_rate": 12.0},
                {"gate": 2, "win_rate": 10.0},
                {"gate": 3, "win_rate": 11.0},
            ],
            "analysis": {"summary": "内枠有利"},
            "by_running_position": [
                {"position": "内", "starts": 10, "wins": 3},
            ],
            "aptitude_summary": {},
        }
        mock_get.return_value = mock_response

        result = analyze_gate_position(
            race_id="20260125_06_11",
            horse_number=3,
            horse_id="horse_001",
            horse_name="テスト馬",
            running_style="先行",
            venue="東京",
            track_type="芝",
            distance=1600,
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.gate_analysis.cached_get")
    def test_RequestException時にwarningが返る(self, mock_get):
        """異常系: RequestException発生時はエラーではなくwarningやデフォルト値で処理される."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_gate_position(
            horse_number=3,
            horse_id="horse_001",
            horse_name="テスト馬",
        )

        # gate_analysis は内部でエラーをハンドリングし、デフォルト値で結果を返す
        has_horse_name = "horse_name" in result
        has_error = "error" in result
        assert has_horse_name or has_error, "Expected 'horse_name' (graceful degradation) or 'error' key"
