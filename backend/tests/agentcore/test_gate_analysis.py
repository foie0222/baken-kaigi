"""枠順分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.gate_analysis import analyze_gate_position
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeGatePosition:
    """枠順分析統合テスト."""

    def test_正常系_枠順を分析(self):
        """正常系: 枠順データを正しく分析できる."""
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

        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["horse_name"] == "テスト馬"
        assert "gate_info" in result
        assert "course_gate_tendency" in result
        assert "horse_gate_aptitude" in result
        assert "running_style_fit" in result

    def test_枠番が正しく計算される(self):
        """馬番から枠番が正しく計算される."""
        result = analyze_gate_position(
            horse_number=3,
            horse_name="テスト馬",
        )

        assert result["gate_info"]["gate"] == 2
        assert result["gate_info"]["position_type"] == "内枠"

    def test_外枠の判定(self):
        """馬番13以上は外枠と判定される."""
        result = analyze_gate_position(
            horse_number=15,
            horse_name="外枠馬",
        )

        assert result["gate_info"]["position_type"] == "外枠"

    def test_馬番0の場合はデフォルト値(self):
        """馬番0の場合はデフォルト値で処理される."""
        result = analyze_gate_position(
            horse_number=0,
            horse_name="テスト馬",
        )

        assert "error" not in result
        assert result["gate_info"]["position_type"] == "不明"

    def test_例外時にエラーを返す(self):
        """異常系: 内部例外発生時はerrorを返す."""
        with patch("tools.gate_analysis._get_position_type", side_effect=Exception("test error")):
            result = analyze_gate_position(
                horse_number=3,
                horse_name="テスト馬",
            )

        assert "error" in result
