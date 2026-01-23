"""過去データ分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# strandsモジュールが利用できない場合はスキップ
try:
    # agentcoreモジュールをインポートできるようにパスを追加
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

    from tools.historical_analysis import (
        _to_track_code,
        _analyze_race_tendency,
        analyze_past_race_trends,
    )
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestToTrackCode:
    """トラックコード変換のテスト."""

    def test_芝はコード1を返す(self):
        assert _to_track_code("芝") == "1"

    def test_ダートはコード2を返す(self):
        assert _to_track_code("ダート") == "2"

    def test_ダ短縮表記はコード2を返す(self):
        assert _to_track_code("ダ") == "2"

    def test_障害はコード3を返す(self):
        assert _to_track_code("障害") == "3"

    def test_未知のコードはデフォルトで1を返す(self):
        assert _to_track_code("未知") == "1"


class TestAnalyzeRaceTendency:
    """レース傾向分析のテスト."""

    def test_勝率35以上は堅いレース(self):
        first_pop = {"win_rate": 40, "place_rate": 70}
        result = _analyze_race_tendency(first_pop)
        assert "堅いレース" in result

    def test_勝率20以下は荒れやすいレース(self):
        first_pop = {"win_rate": 15, "place_rate": 45}
        result = _analyze_race_tendency(first_pop)
        assert "荒れやすいレース" in result

    def test_勝率21から34は標準的なレース(self):
        first_pop = {"win_rate": 28, "place_rate": 55}
        result = _analyze_race_tendency(first_pop)
        assert "標準的なレース" in result

    def test_データがない場合はデータ不足(self):
        result = _analyze_race_tendency(None)
        assert result == "データ不足"


class TestAnalyzePastRaceTrends:
    """analyze_past_race_trends統合テスト."""

    @patch("tools.historical_analysis.requests.get")
    def test_正常なAPI応答で分析結果を返す(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "total_races": 100,
            "popularity_stats": [
                {
                    "popularity": 1,
                    "total_runs": 100,
                    "wins": 33,
                    "places": 60,
                    "win_rate": 33.0,
                    "place_rate": 60.0,
                },
                {
                    "popularity": 2,
                    "total_runs": 100,
                    "wins": 18,
                    "places": 45,
                    "win_rate": 18.0,
                    "place_rate": 45.0,
                },
            ],
            "avg_win_payout": None,
            "avg_place_payout": None,
            "conditions": {
                "track_code": "1",
                "distance": 1600,
                "grade_code": None,
            },
        }
        mock_get.return_value = mock_response

        result = analyze_past_race_trends.func(
            race_id="202601050811",
            track_type="芝",
            distance=1600,
            grade_class="未勝利",
        )

        assert result["race_id"] == "202601050811"
        assert result["total_races_analyzed"] == 100
        assert "first_popularity" in result
        assert "race_tendency" in result
        assert "popularity_trends" in result
        assert len(result["popularity_trends"]) == 2

    @patch("tools.historical_analysis.requests.get")
    def test_404レスポンスで警告を返す(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = analyze_past_race_trends.func(
            race_id="202601050811",
            track_type="芝",
            distance=1600,
            grade_class="新馬",
        )

        assert "warning" in result
        assert result["race_id"] == "202601050811"

    @patch("tools.historical_analysis.requests.get")
    def test_APIエラーでエラーを返す(self, mock_get):
        import requests as real_requests
        mock_get.side_effect = real_requests.RequestException("Connection error")

        result = analyze_past_race_trends.func(
            race_id="202601050811",
            track_type="芝",
            distance=1600,
            grade_class="G1",
        )

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]
