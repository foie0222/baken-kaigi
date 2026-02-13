"""馬分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# strandsモジュールが利用できない場合はスキップ
try:
    # agentcoreモジュールをインポートできるようにパスを追加
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

    from tools.horse_analysis import (
        analyze_horse_performance,
        _evaluate_form,
        _analyze_ability,
        _analyze_class,
        _analyze_distance,
    )
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestEvaluateForm:
    """調子評価のテスト."""

    def test_好調と判定される(self):
        """直近成績が良好な場合、好調と判定."""
        finishes = [1, 2, 1, 3, 2]  # 全て馬券圏内、平均1.8
        result = _evaluate_form(finishes)
        assert result == "好調"

    def test_上昇中と判定される(self):
        """改善傾向がある場合、上昇中と判定."""
        finishes = [2, 4, 6]  # 直近2着 < 3走前6着で改善傾向
        result = _evaluate_form(finishes)
        assert result == "上昇中"

    def test_不調と判定される(self):
        """成績が悪い場合、不調と判定."""
        finishes = [10, 12, 8, 15, 9]  # 馬券圏内なし
        result = _evaluate_form(finishes)
        assert result == "不調"

    def test_データなしと判定される(self):
        """データがない場合."""
        result = _evaluate_form([])
        assert result == "データなし"


class TestAnalyzeAbility:
    """能力分析のテスト."""

    def test_上がり3Fが速い場合はA評価(self):
        """上がり3F平均が33.5秒以下ならA."""
        performances = [
            {"last_3f": 33.0, "finish_position": 1},
            {"last_3f": 33.2, "finish_position": 2},
        ]
        result = _analyze_ability(performances)
        assert result["finishing_speed"] == "A"

    def test_着順の安定性が高い(self):
        """着順のばらつきが小さい場合は安定性が高い."""
        performances = [
            {"finish_position": 2, "last_3f": 34.0},
            {"finish_position": 3, "last_3f": 34.1},
            {"finish_position": 2, "last_3f": 34.2},
        ]
        result = _analyze_ability(performances)
        assert result["consistency"] == "高い"

    def test_長距離でスタミナA評価(self):
        """長距離で平均3着以内ならスタミナA."""
        performances = [
            {"distance": 2400, "finish_position": 1, "last_3f": 34.0},
            {"distance": 2200, "finish_position": 2, "last_3f": 34.1},
        ]
        result = _analyze_ability(performances)
        assert result["stamina"] == "A"


class TestAnalyzeClass:
    """クラス分析のテスト."""

    def test_現在クラスを検出(self):
        """最頻出クラスを現在クラスとして検出."""
        performances = [
            {"grade_class": "2勝", "finish_position": 3},
            {"grade_class": "2勝", "finish_position": 2},
            {"grade_class": "1勝", "finish_position": 1},
        ]
        result = _analyze_class(performances)
        assert result["current_class"] == "2勝"

    def test_クラス上昇余地あり(self):
        """現クラスで平均2.5着以内なら上昇余地あり."""
        performances = [
            {"grade_class": "2勝", "finish_position": 1},
            {"grade_class": "2勝", "finish_position": 2},
        ]
        result = _analyze_class(performances)
        assert result["class_up_potential"] is True


class TestAnalyzeDistance:
    """距離適性分析のテスト."""

    def test_短距離が得意(self):
        """短距離成績が良い場合."""
        performances = [
            {"distance": 1400, "finish_position": 1},
            {"distance": 1200, "finish_position": 2},
        ]
        result = _analyze_distance(performances)
        assert result["short_performance"] == "得意"

    def test_中距離が得意(self):
        """中距離成績が良い場合."""
        performances = [
            {"distance": 1800, "finish_position": 1},
            {"distance": 1600, "finish_position": 2},
        ]
        result = _analyze_distance(performances)
        assert result["middle_performance"] == "得意"


class TestAnalyzeHorsePerformance:
    """analyze_horse_performance 統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_正常系_馬の成績を分析(self, mock_get_perfs):
        """正常系: DynamoDBからデータ取得成功時、分析結果を返す."""
        mock_get_perfs.return_value = [
            {
                "finish_position": 1,
                "distance": 1600,
                "last_3f": 33.5,
                "grade_class": "2勝",
            },
            {
                "finish_position": 2,
                "distance": 1800,
                "last_3f": 33.8,
                "grade_class": "2勝",
            },
        ]

        result = analyze_horse_performance("horse_001", "テスト馬")

        assert result["horse_name"] == "テスト馬"
        assert "recent_form" in result
        assert "form_rating" in result
        assert "ability_analysis" in result
        assert "comment" in result

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_データなしで警告を返す(self, mock_get_perfs):
        """データが空の場合は警告を返す."""
        mock_get_perfs.return_value = []

        result = analyze_horse_performance("horse_999", "不明馬")

        assert "warning" in result
        assert "過去成績がありません" in result["warning"]

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_例外時にエラーを返す(self, mock_get_perfs):
        """Exception発生時はerrorを含む辞書を返す."""
        mock_get_perfs.side_effect = Exception("Connection failed")

        result = analyze_horse_performance("horse_001", "テスト馬")

        assert "error" in result

    @patch("tools.dynamodb_client.get_horse_performances")
    def test_limit引数が適切に適用される(self, mock_get_perfs):
        """limit引数がDynamoDB呼び出しに適用されることを確認."""
        mock_get_perfs.return_value = []

        analyze_horse_performance("horse_001", "テスト馬", limit=10)

        mock_get_perfs.assert_called_once_with("horse_001", limit=10)
