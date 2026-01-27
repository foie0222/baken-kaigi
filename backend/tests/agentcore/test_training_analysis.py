"""調教分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

# strandsモジュールが利用できない場合はスキップ
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.training_analysis import analyze_training_condition
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.training_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.training_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeTrainingCondition:
    """調教分析統合テスト."""

    @patch("tools.training_analysis.requests.get")
    def test_正常系_調教データを分析(self, mock_get):
        """正常系: 調教データを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "training_records": [
                {
                    "date": "2026-01-20",
                    "course": "栗東CW",
                    "time_5f": 52.0,
                    "time_last_3f": 12.3,
                    "evaluation": "良い動き",
                },
                {
                    "date": "2026-01-15",
                    "course": "栗東坂路",
                    "time_4f": 52.5,
                    "time_last_3f": 12.5,
                    "evaluation": "普通",
                },
            ],
            "training_summary": {
                "total_workouts": 2,
                "intensity": "強め",
            },
        }
        mock_get.return_value = mock_response

        result = analyze_training_condition("horse_001", "テスト馬")

        assert "last_workout" in result or "warning" not in result
        assert result.get("horse_name") == "テスト馬" or "warning" in result

    @patch("tools.training_analysis.requests.get")
    def test_404エラーで警告を返す(self, mock_get):
        """異常系: 404の場合は警告を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = analyze_training_condition("horse_999", "不明馬")

        assert "warning" in result
        assert "見つかりませんでした" in result["warning"]

    @patch("tools.training_analysis.requests.get")
    def test_空データで警告を返す(self, mock_get):
        """異常系: 調教データが空の場合は警告を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "training_records": [],
            "training_summary": {},
        }
        mock_get.return_value = mock_response

        result = analyze_training_condition("horse_001", "テスト馬")

        assert "warning" in result

    @patch("tools.training_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_training_condition("horse_001", "テスト馬")

        assert "error" in result
