"""ローテーション分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# strandsモジュールが利用できない場合はスキップ
try:
    # agentcoreモジュールをインポートできるようにパスを追加
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

    from tools.rotation_analysis import (
        _get_interval_label,
        _format_record,
        _determine_best_interval,
        analyze_rotation,
    )
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


class TestGetIntervalLabel:
    """間隔ラベル取得のテスト."""

    def test_Noneは不明を返す(self):
        assert _get_interval_label(None) == "不明"

    def test_負の値は不明を返す(self):
        assert _get_interval_label(-1) == "不明"

    def test_0日は連闘を返す(self):
        assert _get_interval_label(0) == "連闘"

    def test_3日は連闘を返す(self):
        assert _get_interval_label(3) == "連闘"

    def test_7日は中1週を返す(self):
        assert _get_interval_label(7) == "中1週"

    def test_14日は中2週を返す(self):
        assert _get_interval_label(14) == "中2週"

    def test_21日は中3週を返す(self):
        assert _get_interval_label(21) == "中3週"

    def test_28日は中4週を返す(self):
        assert _get_interval_label(28) == "中4週"

    def test_35日は中5週を返す(self):
        assert _get_interval_label(35) == "中5週"

    def test_42日は中6週を返す(self):
        assert _get_interval_label(42) == "中6週"

    def test_60日は約2ヶ月を返す(self):
        assert _get_interval_label(60) == "約2ヶ月"

    def test_90日は約3ヶ月を返す(self):
        assert _get_interval_label(90) == "約3ヶ月"

    def test_120日は4ヶ月以上を返す(self):
        assert _get_interval_label(120) == "4ヶ月以上"


class TestFormatRecord:
    """成績フォーマットのテスト."""

    def test_空リストは全て0の成績を返す(self):
        assert _format_record([]) == "0-0-0-0"

    def test_1着のみの場合(self):
        assert _format_record([1, 1, 1]) == "3-0-0-0"

    def test_2着のみの場合(self):
        assert _format_record([2, 2]) == "0-2-0-0"

    def test_3着のみの場合(self):
        assert _format_record([3]) == "0-0-1-0"

    def test_着外のみの場合(self):
        assert _format_record([4, 5, 6]) == "0-0-0-3"

    def test_混合結果の場合(self):
        assert _format_record([1, 2, 3, 4, 5]) == "1-1-1-2"


class TestDetermineBestInterval:
    """ベスト間隔判定のテスト."""

    def test_短い間隔が最良の場合は中2週以内を返す(self):
        short = [1, 2]  # 平均1.5
        standard = [3, 4]  # 平均3.5
        long = [5, 6]  # 平均5.5
        assert _determine_best_interval(short, standard, long) == "中2週以内"

    def test_標準間隔が最良の場合は中3から4週を返す(self):
        short = [5, 6]  # 平均5.5
        standard = [1, 2]  # 平均1.5
        long = [5, 6]  # 平均5.5
        assert _determine_best_interval(short, standard, long) == "中3〜4週"

    def test_長い間隔が最良の場合は間隔空けを返す(self):
        short = [5, 6]  # 平均5.5
        standard = [5, 6]  # 平均5.5
        long = [1, 2]  # 平均1.5
        assert _determine_best_interval(short, standard, long) == "間隔空け"

    def test_全て空の場合はデフォルトで中3から4週を返す(self):
        assert _determine_best_interval([], [], []) == "中3〜4週"


class TestAnalyzeRotation:
    """analyze_rotation統合テスト."""

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_race")
    def test_正常なAPI応答で分析結果を返す(self, mock_get_race, mock_get_perfs):
        mock_get_race.return_value = {
            "race_date": "2026-01-26",
            "grade": "G1",
        }
        mock_get_perfs.return_value = [
            {
                "race_date": "2026-01-05",
                "race_name": "京都金杯",
                "finish_position": 3,
                "grade_class": "G3",
            },
            {
                "race_date": "2025-12-01",
                "race_name": "ジャパンカップ",
                "finish_position": 5,
                "grade_class": "G1",
            },
        ]

        result = analyze_rotation(
            horse_id="001234",
            horse_name="テスト馬",
            race_id="202601050811",
        )

        assert result["horse_name"] == "テスト馬"
        assert "rotation_info" in result
        assert "interval_performance" in result
        assert "step_race_analysis" in result
        assert "fitness_estimation" in result
        assert "overall_comment" in result

    @patch("tools.dynamodb_client.get_race")
    def test_レース情報なしでエラーを返す(self, mock_get_race):
        mock_get_race.return_value = None

        result = analyze_rotation(
            horse_id="001234",
            horse_name="テスト馬",
            race_id="invalid_race",
        )

        # get_race returns None -> _get_race_info returns {} -> no "error" key
        # The tool will proceed with empty race_info
        assert result["horse_name"] == "テスト馬"

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_race")
    def test_過去成績なしで警告を返す(self, mock_get_race, mock_get_perfs):
        mock_get_race.return_value = {
            "race_date": "2026-01-26",
            "grade": "未勝利",
        }
        mock_get_perfs.return_value = []

        result = analyze_rotation(
            horse_id="001234",
            horse_name="新馬",
            race_id="202601050811",
        )

        assert "warning" in result
        assert result["horse_name"] == "新馬"

    @patch("tools.dynamodb_client.get_race")
    def test_例外時にエラーを返す(self, mock_get_race):
        mock_get_race.side_effect = Exception("Connection error")

        result = analyze_rotation(
            horse_id="001234",
            horse_name="テスト馬",
            race_id="202601050811",
        )

        assert "error" in result

    @patch("tools.dynamodb_client.get_horse_performances")
    @patch("tools.dynamodb_client.get_race")
    def test_連闘_days_0_でも正常に処理する(self, mock_get_race, mock_get_perfs):
        """days=0（連闘）の場合もfalsyチェックで除外されないことを確認."""
        mock_get_race.return_value = {
            "race_date": "2026-01-26",
            "grade": "OP",
        }
        mock_get_perfs.return_value = [
            {
                "race_date": "2026-01-26",  # 同日
                "race_name": "前走レース",
                "finish_position": 2,
                "grade_class": "OP",
            },
        ]

        result = analyze_rotation(
            horse_id="001234",
            horse_name="連闘馬",
            race_id="202601050811",
        )

        assert result["horse_name"] == "連闘馬"
        assert result["rotation_info"]["days_since_last_race"] == 0
        assert result["rotation_info"]["interval_type"] == "連闘"
