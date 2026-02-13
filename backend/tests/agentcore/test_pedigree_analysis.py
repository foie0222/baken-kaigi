"""血統分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.pedigree_analysis import analyze_pedigree_aptitude
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestAnalyzePedigreeAptitude:
    """血統適性分析統合テスト."""

    @patch("tools.dynamodb_client.get_horse")
    def test_正常系_血統を分析(self, mock_get_horse):
        """正常系: 血統データを正しく分析できる."""
        mock_get_horse.return_value = {
            "horse_id": "horse_001",
            "horse_name": "テスト馬",
            "sire_name": "ディープインパクト",
            "dam_sire_name": "キングカメハメハ",
        }

        result = analyze_pedigree_aptitude(
            "horse_001", "テスト馬",
            race_distance=2000,
            track_type="芝",
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["horse_name"] == "テスト馬"
        assert "pedigree_summary" in result
        assert "distance_aptitude" in result
        assert "track_aptitude" in result

    @patch("tools.dynamodb_client.get_horse")
    def test_馬データなしで警告を返す(self, mock_get_horse):
        """異常系: 馬データがない場合はwarningを返す."""
        mock_get_horse.return_value = None

        result = analyze_pedigree_aptitude("horse_999", "不明馬")

        assert "warning" in result

    @patch("tools.dynamodb_client.get_horse")
    def test_DynamoDB例外時にエラーを返す(self, mock_get_horse):
        """異常系: DynamoDB例外発生時はerrorを返す."""
        mock_get_horse.side_effect = Exception("Connection failed")

        result = analyze_pedigree_aptitude("horse_001", "テスト馬")

        assert "error" in result
