"""種牡馬分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.sire_analysis import analyze_sire_offspring
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzeSireOffspring:
    """種牡馬分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse")
    def test_正常系_種牡馬を分析(self, mock_get_horse):
        """正常系: 種牡馬データを正しく分析できる."""
        mock_get_horse.return_value = {
            "horse_id": "horse_001",
            "horse_name": "テスト馬",
            "sire_name": "ディープインパクト",
            "dam_sire_name": "キングカメハメハ",
        }

        result = analyze_sire_offspring(
            horse_id="horse_001",
            horse_name="テスト馬",
            sire_name="ディープインパクト",
            track_type="芝",
            race_distance=2000,
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["horse_name"] == "テスト馬"
        assert "sire_analysis" in result
        assert "condition_aptitude" in result
        assert "nicks_analysis" in result
        assert "growth_analysis" in result

    def test_horse_idなしでもデフォルト分析(self):
        """horse_idが空でもデフォルト値で分析できる."""
        result = analyze_sire_offspring(
            horse_name="テスト馬",
            sire_name="ディープインパクト",
            track_type="芝",
            race_distance=2000,
        )

        assert "error" not in result
        assert result["sire_analysis"]["sire_name"] == "ディープインパクト"

    @patch("tools.dynamodb_client.get_horse")
    def test_DynamoDB例外時にエラーを返す(self, mock_get_horse):
        """異常系: DynamoDB例外発生時はerrorを返す."""
        mock_get_horse.side_effect = Exception("DynamoDB error")

        result = analyze_sire_offspring(
            horse_id="horse_001",
            horse_name="テスト馬",
            sire_name="ディープインパクト",
        )

        assert "error" in result
