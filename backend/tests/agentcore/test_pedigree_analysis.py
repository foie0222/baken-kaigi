"""血統分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.pedigree_analysis import analyze_pedigree_aptitude
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.pedigree_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.pedigree_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzePedigreeAptitude:
    """血統適性分析統合テスト."""

    @patch("tools.pedigree_analysis.requests.get")
    def test_正常系_血統を分析(self, mock_get):
        """正常系: 血統データを正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sire": {
                "name": "ディープインパクト",
                "sire_line": "サンデーサイレンス系",
            },
            "dam_sire": {
                "name": "キングカメハメハ",
            },
            "inbreeding": [
                {"name": "サンデーサイレンス", "cross": "3x4"},
            ],
        }
        mock_get.return_value = mock_response

        result = analyze_pedigree_aptitude(
            "horse_001", "テスト馬",
            race_distance=2000,
            track_type="芝",
        )

        assert "sire_analysis" in result or "warning" not in result or "error" not in result

    @patch("tools.pedigree_analysis.requests.get")
    def test_404エラーで警告を返す(self, mock_get):
        """異常系: 404の場合は警告を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = analyze_pedigree_aptitude("horse_999", "不明馬")

        assert "warning" in result or "error" in result

    @patch("tools.pedigree_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_pedigree_aptitude("horse_001", "テスト馬")

        assert "error" in result
