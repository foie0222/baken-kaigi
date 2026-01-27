"""前走分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.last_race_analysis import analyze_last_race_detail
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.last_race_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.last_race_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeLastRaceDetail:
    """前走分析統合テスト."""

    @patch("tools.last_race_analysis.requests.get")
    def test_正常系_前走を分析(self, mock_get):
        """正常系: 前走データを正しく分析できる."""
        # 1回目: レース情報取得
        mock_race_response = MagicMock()
        mock_race_response.status_code = 200
        mock_race_response.json.return_value = {
            "race_name": "今回のレース",
            "distance": 1600,
            "track_type": "芝",
            "track_condition": "良",
            "grade_class": "3勝",
            "venue": "東京",
        }
        mock_race_response.raise_for_status = MagicMock()

        # 2回目: 過去成績取得
        mock_perf_response = MagicMock()
        mock_perf_response.status_code = 200
        mock_perf_response.json.return_value = {
            "performances": [
                {
                    "race_name": "前走レース",
                    "finish_position": 2,
                    "margin": "クビ",
                    "distance": 1600,
                    "track_type": "芝",
                    "track_condition": "良",
                    "venue": "東京",
                    "race_date": "2026-01-10",
                    "last_3f": "33.8",
                    "time": "1:33.5",
                    "popularity": 2,
                    "odds": 5.0,
                    "grade_class": "3勝",
                    "total_runners": 16,
                },
            ]
        }
        mock_perf_response.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_race_response, mock_perf_response]

        result = analyze_last_race_detail(
            horse_id="horse_001",
            horse_name="テスト馬",
            race_id="20260125_06_11",
        )

        assert "error" not in result or "warning" in result

    @patch("tools.last_race_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_last_race_detail(
            horse_id="horse_001",
            horse_name="テスト馬",
            race_id="20260125_06_11",
        )

        assert "error" in result
