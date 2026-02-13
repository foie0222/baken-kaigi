"""調教分析ツールのテスト."""

import sys
from pathlib import Path

import pytest

# strandsモジュールが利用できない場合はスキップ
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.training_analysis import analyze_training_condition
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeTrainingCondition:
    """調教分析統合テスト."""

    def test_常にwarningを返す(self):
        """DynamoDBに調教テーブルがないためスタブ化。常にwarningを返す."""
        result = analyze_training_condition("horse_001", "テスト馬")

        assert "warning" in result
        assert "調教データがありません" in result["warning"]
        assert result["horse_name"] == "テスト馬"

    def test_race_id指定でもwarningを返す(self):
        """race_idを指定しても同じくwarningを返す."""
        result = analyze_training_condition("horse_001", "テスト馬", race_id="20260125_06_11")

        assert "warning" in result
