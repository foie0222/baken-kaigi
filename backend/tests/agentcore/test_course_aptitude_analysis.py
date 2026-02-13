"""コース適性分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.course_aptitude_analysis import analyze_course_aptitude
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeCourseAptitude:
    """コース適性分析統合テスト."""

    def test_正常系_コース適性を分析(self):
        """正常系: コース適性データを正しく分析できる（スタブモード）."""
        result = analyze_course_aptitude(
            horse_id="horse_001",
            horse_name="テスト馬",
            venue="東京",
            track_type="芝",
            distance=1600,
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["horse_name"] == "テスト馬"
        assert "venue_aptitude" in result
        assert "distance_aptitude" in result
        assert "overall_aptitude" in result

    def test_全項目にrating含む(self):
        """各適性にrating評価が含まれる."""
        result = analyze_course_aptitude(
            horse_id="horse_001",
            horse_name="テスト馬",
            venue="東京",
            distance=1600,
        )

        assert "venue_rating" in result["venue_aptitude"]
        assert "distance_rating" in result["distance_aptitude"]
        assert "rating" in result["overall_aptitude"]

    def test_例外時にエラーを返す(self):
        """異常系: 内部例外発生時はerrorを返す."""
        with patch("tools.course_aptitude_analysis._analyze_venue_aptitude",
                    side_effect=Exception("test error")):
            result = analyze_course_aptitude(
                horse_id="horse_001",
                horse_name="テスト馬",
            )

        assert "error" in result
