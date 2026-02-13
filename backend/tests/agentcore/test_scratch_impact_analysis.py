"""出走取消影響分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.scratch_impact_analysis import analyze_scratch_impact
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_dynamodb_client():
    """DynamoDBクライアントをモック化."""
    with patch("tools.scratch_impact_analysis.dynamodb_client") as mock_client:
        mock_client.get_race.return_value = {}
        mock_client.get_runners.return_value = []
        yield mock_client


class TestAnalyzeScratchImpact:
    """出走取消影響分析統合テスト."""

    def test_正常系_取消影響を分析(self, mock_dynamodb_client):
        """正常系: 出走取消の影響を正しく分析できる."""
        mock_dynamodb_client.get_race.return_value = {
            "race_name": "テストレース",
            "distance": 1600,
            "track_type": "芝",
        }
        mock_dynamodb_client.get_runners.return_value = [
            {"horse_number": 1, "horse_name": "馬1", "running_style": "逃げ", "popularity": 1, "odds": 2.5},
            {"horse_number": 2, "horse_name": "馬2", "running_style": "先行", "popularity": 2, "odds": 5.0},
            {"horse_number": 5, "horse_name": "取消馬", "running_style": "差し", "popularity": 3, "odds": 8.0},
        ]

        result = analyze_scratch_impact(
            race_id="20260125_06_11",
            scratched_horses=[{"horse_number": 5, "horse_name": "取消馬", "reason": "取消"}],
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    def test_Exception時にエラーを返す(self, mock_dynamodb_client):
        """異常系: Exception発生時はerrorを返す."""
        mock_dynamodb_client.get_race.side_effect = Exception("Connection failed")

        result = analyze_scratch_impact(
            race_id="20260125_06_11",
            scratched_horses=[{"horse_number": 5, "horse_name": "取消馬", "reason": "取消"}],
        )

        assert "error" in result
