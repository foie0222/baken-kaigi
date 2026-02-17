"""展開分析ツールのテスト."""

import sys
from pathlib import Path

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

# strands の @tool デコレータをモック
mock_strands = type(sys)("strands")
mock_strands.tool = lambda f: f  # type: ignore
sys.modules["strands"] = mock_strands

from tools.pace_analysis import (
    _analyze_race_development_impl,
    _analyze_odds_gap,
    _analyze_post_position,
    _generate_development_summary,
    _analyze_race_characteristics_impl,
)


class TestAnalyzeRaceDevelopmentImpl:
    """展開分析の実装テスト."""

    def test_脚質データなしでエラー(self):
        result = _analyze_race_development_impl("test_race", [])
        assert "error" in result

    def test_正常な展開分析(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "逃げ馬1", "running_style": "逃げ"},
            {"horse_number": 2, "horse_name": "逃げ馬2", "running_style": "逃げ"},
            {"horse_number": 3, "horse_name": "逃げ馬3", "running_style": "逃げ"},
            {"horse_number": 4, "horse_name": "先行馬", "running_style": "先行"},
            {"horse_number": 5, "horse_name": "差し馬", "running_style": "差し"},
            {"horse_number": 6, "horse_name": "追込馬", "running_style": "追込"},
        ]
        result = _analyze_race_development_impl("test_race", running_styles)

        assert result["race_id"] == "test_race"
        assert result["front_runner_count"] == 3
        assert result["total_runners"] == 6
        assert result["running_style_summary"] == {"逃げ": 3, "先行": 1, "差し": 1, "追込": 1}
        assert len(result["runners_by_style"]["逃げ"]) == 3
        assert len(result["runners_by_style"]["先行"]) == 1
        assert len(result["runners_by_style"]["差し"]) == 1
        assert len(result["runners_by_style"]["追込"]) == 1

    def test_逃げ馬1頭の脚質構成サマリー(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "逃げ馬", "running_style": "逃げ"},
            {"horse_number": 2, "horse_name": "先行馬1", "running_style": "先行"},
            {"horse_number": 3, "horse_name": "先行馬2", "running_style": "先行"},
            {"horse_number": 4, "horse_name": "差し馬", "running_style": "差し"},
        ]
        result = _analyze_race_development_impl("test_race", running_styles)

        assert result["running_style_summary"] == {"逃げ": 1, "先行": 2, "差し": 1}
        assert result["front_runner_count"] == 1


class TestAnalyzeOddsGap:
    """オッズ断層分析のテスト."""

    def test_4頭未満でNone(self):
        result = _analyze_odds_gap([{"odds": 2.0}, {"odds": 3.0}])
        assert result is None

    def test_大きな断層で堅い判定(self):
        runners = [
            {"odds": 2.0},
            {"odds": 3.5},
            {"odds": 5.0},
            {"odds": 20.0},
        ]
        result = _analyze_odds_gap(runners)
        assert result is not None
        assert result["adjustment"] == -1
        assert "断層" in result["comment"]

    def test_団子状態で荒れ判定(self):
        runners = [
            {"odds": 3.0},
            {"odds": 3.5},
            {"odds": 5.0},
            {"odds": 7.0},
        ]
        result = _analyze_odds_gap(runners)
        assert result is not None
        assert result["adjustment"] == 1
        assert "団子" in result["comment"]

    def test_通常のオッズ分布でNone(self):
        runners = [
            {"odds": 2.0},
            {"odds": 5.0},
            {"odds": 8.0},
            {"odds": 12.0},
        ]
        result = _analyze_odds_gap(runners)
        assert result is None

    def test_オッズ0を除外(self):
        runners = [
            {"odds": 0},
            {"odds": 2.0},
            {"odds": 3.0},
            {"odds": 5.0},
        ]
        result = _analyze_odds_gap(runners)
        # 有効なオッズが3つしかないのでNone
        assert result is None


class TestAnalyzePostPosition:
    """枠順分析のテスト."""

    def test_芝の内枠で有利(self):
        result = _analyze_post_position(1, 16, "芝")
        assert result["position_group"] == "内枠"
        assert result["advantage"] == "有利"

    def test_芝の外枠で不利(self):
        result = _analyze_post_position(16, 16, "芝")
        assert result["position_group"] == "外枠"
        assert result["advantage"] == "不利"

    def test_芝の中枠で中立(self):
        result = _analyze_post_position(8, 16, "芝")
        assert result["position_group"] == "中枠"
        assert result["advantage"] == "中立"

    def test_ダートの外枠で有利(self):
        result = _analyze_post_position(16, 16, "ダート")
        assert result["position_group"] == "外枠"
        assert result["advantage"] == "有利"

    def test_ダートの内枠で不利(self):
        result = _analyze_post_position(1, 16, "ダート")
        assert result["position_group"] == "内枠"
        assert result["advantage"] == "不利"

    def test_出走頭数0で不明(self):
        result = _analyze_post_position(1, 0, "芝")
        assert result["advantage"] == "中立"
        assert "不明" in result["comment"]

    def test_馬場情報なしで中立(self):
        result = _analyze_post_position(1, 16, "")
        assert result["advantage"] == "中立"


class TestGenerateDevelopmentSummary:
    """展開サマリー生成のテスト."""

    def test_逃げ馬3頭以上のサマリー(self):
        runners_by_style = {
            "逃げ": [
                {"horse_name": "馬A"},
                {"horse_name": "馬B"},
                {"horse_name": "馬C"},
            ],
            "先行": [],
            "差し": [],
            "追込": [],
        }
        summary = _generate_development_summary(
            runners_by_style, "芝", 16
        )
        assert "逃げ馬が3頭" in summary
        assert "馬A" in summary

    def test_逃げ馬1頭のサマリー(self):
        runners_by_style = {
            "逃げ": [{"horse_name": "スプリンター"}],
            "先行": [{"horse_name": "先行馬"}],
            "差し": [],
            "追込": [],
        }
        summary = _generate_development_summary(
            runners_by_style, "ダート", 12
        )
        assert "スプリンター" in summary
        assert "1頭のみ" in summary
        assert "ダート" in summary

    def test_逃げ馬なしのサマリー(self):
        runners_by_style = {
            "逃げ": [],
            "先行": [{"horse_name": "先行馬A"}],
            "差し": [],
            "追込": [],
        }
        summary = _generate_development_summary(
            runners_by_style, "芝", 10
        )
        assert "逃げ馬が不在" in summary
        assert "先行馬A" in summary

    def test_逃げ馬2頭のサマリー(self):
        runners_by_style = {
            "逃げ": [{"horse_name": "馬A"}, {"horse_name": "馬B"}],
            "先行": [],
            "差し": [],
            "追込": [],
        }
        summary = _generate_development_summary(
            runners_by_style, "芝", 14
        )
        assert "逃げ馬が2頭" in summary


class TestAnalyzeRaceCharacteristicsImpl:
    """レース特性分析の統合テスト."""

    def _make_running_styles(self):
        return [
            {"horse_number": 1, "horse_name": "逃げ馬", "running_style": "逃げ"},
            {"horse_number": 2, "horse_name": "先行馬", "running_style": "先行"},
            {"horse_number": 3, "horse_name": "差し馬", "running_style": "差し"},
            {"horse_number": 4, "horse_name": "追込馬", "running_style": "追込"},
            {"horse_number": 5, "horse_name": "自在馬", "running_style": "自在"},
        ]

    def test_全項目が返却される(self):
        result = _analyze_race_characteristics_impl(
            "test_race",
            self._make_running_styles(),
            venue="東京",
            surface="芝",
        )
        assert "development" in result
        assert "post_position" in result
        assert "summary" in result

    def test_展開分析に脚質構成サマリーが含まれる(self):
        result = _analyze_race_characteristics_impl(
            "test_race",
            self._make_running_styles(),
            surface="芝",
        )
        dev = result["development"]
        assert dev["running_style_summary"] == {"逃げ": 1, "先行": 1, "差し": 1, "追込": 1, "自在": 1}
        assert dev["front_runner_count"] == 1
        assert dev["total_runners"] == 5

    def test_枠順分析が選択馬のみ(self):
        result = _analyze_race_characteristics_impl(
            "test_race",
            self._make_running_styles(),
            surface="芝",
            horse_numbers=[1, 3],
        )
        assert len(result["post_position"]) == 2
        positions = [p["horse_number"] for p in result["post_position"]]
        assert 1 in positions
        assert 3 in positions

    def test_サマリーが自然言語(self):
        result = _analyze_race_characteristics_impl(
            "test_race",
            self._make_running_styles(),
            venue="東京",
            surface="芝",
        )
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 20

    def test_脚質データなしでエラー(self):
        result = _analyze_race_characteristics_impl("test_race", [])
        assert "error" in result

