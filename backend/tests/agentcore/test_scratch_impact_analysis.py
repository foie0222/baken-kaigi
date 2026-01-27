"""出走取消影響分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.scratch_impact_analysis import analyze_scratch_impact
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.scratch_impact_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.scratch_impact_analysis.get_api_url", return_value="https://api.example.com"):
            yield


class TestAnalyzeScratchImpact:
    """出走取消影響分析統合テスト."""

    @patch("tools.scratch_impact_analysis.requests.get")
    def test_正常系_取消影響を分析(self, mock_get):
        """正常系: 出走取消の影響を正しく分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "race": {"race_name": "テストレース", "distance": 1600},
            "runners": [
                {"horse_number": 1, "horse_name": "馬1", "running_style": "逃げ"},
                {"horse_number": 2, "horse_name": "馬2", "running_style": "先行"},
            ],
        }
        mock_get.return_value = mock_response

        result = analyze_scratch_impact(
            race_id="20260125_06_11",
            scratched_horses=[{"horse_number": 5, "horse_name": "取消馬", "reason": "取消"}],
        )

        assert "error" not in result or "warning" in result

    @patch("tools.scratch_impact_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_scratch_impact(
            race_id="20260125_06_11",
            scratched_horses=[{"horse_number": 5, "horse_name": "取消馬", "reason": "取消"}],
        )

        assert "error" in result
