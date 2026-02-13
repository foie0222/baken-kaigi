"""過去データ分析ツールのテスト."""

import sys
from pathlib import Path

import pytest

# strandsモジュールが利用できない場合はスキップ
try:
    # agentcoreモジュールをインポートできるようにパスを追加
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

    from tools.historical_analysis import (
        _to_track_code,
        _analyze_race_tendency,
        analyze_past_race_trends,
        analyze_jockey_course_stats,
        analyze_bet_roi,
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

    def test_DynamoDBスタブモードで警告を返す(self):
        """DynamoDBにデータなしで警告を返す."""
        result = analyze_past_race_trends(
            race_id="202601050811",
            track_type="芝",
            distance=1600,
            grade_class="未勝利",
        )

        assert "warning" in result
        assert result["race_id"] == "202601050811"


class TestAnalyzeJockeyCourseStats:
    """騎手コース成績分析のテスト."""

    def test_DynamoDBスタブモードで警告を返す(self):
        """DynamoDBにデータなしで警告を返す."""
        result = analyze_jockey_course_stats(
            jockey_id="00001",
            jockey_name="川田将雅",
            track_type="芝",
            distance=1600,
            venue="阪神",
        )

        assert "warning" in result
        assert result["jockey_name"] == "川田将雅"


class TestAnalyzeBetRoi:
    """買い目回収率分析のテスト."""

    def test_DynamoDBスタブモードで警告を返す(self):
        """DynamoDBにデータなしで警告を返す."""
        result = analyze_bet_roi(
            track_type="芝",
            distance=1600,
            popularity=1,
        )

        assert "warning" in result
