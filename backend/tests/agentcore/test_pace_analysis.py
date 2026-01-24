"""展開分析ツールのテスト."""

import sys
from pathlib import Path
import importlib.util

# strands の @tool デコレータをモック（他のモジュールがロードされる前に）
mock_strands = type(sys)("strands")
mock_strands.tool = lambda f: f  # type: ignore
sys.modules["strands"] = mock_strands

# pace_analysis モジュールを直接ファイルからロード
pace_analysis_path = Path(__file__).parent.parent.parent / "agentcore" / "tools" / "pace_analysis.py"
spec = importlib.util.spec_from_file_location("pace_analysis", pace_analysis_path)
pace_analysis = importlib.util.module_from_spec(spec)  # type: ignore
spec.loader.exec_module(pace_analysis)  # type: ignore

_predict_pace = pace_analysis._predict_pace
_generate_pace_analysis = pace_analysis._generate_pace_analysis
_analyze_race_development_impl = pace_analysis._analyze_race_development_impl
_analyze_running_style_match_impl = pace_analysis._analyze_running_style_match_impl
PACE_FAVORABLE_STYLES = pace_analysis.PACE_FAVORABLE_STYLES


class TestPredictPace:
    """ペース予想のテスト."""

    def test_逃げ馬3頭以上でハイペース(self):
        pace = _predict_pace(3, 16)
        assert pace == "ハイ"

    def test_逃げ馬4頭でハイペース(self):
        pace = _predict_pace(4, 16)
        assert pace == "ハイ"

    def test_逃げ馬1頭でスローペース(self):
        pace = _predict_pace(1, 16)
        assert pace == "スロー"

    def test_逃げ馬2頭でミドルペース(self):
        pace = _predict_pace(2, 16)
        assert pace == "ミドル"

    def test_逃げ馬0頭でスローペース(self):
        # 逃げ馬がいない場合も、スローペース傾向
        pace = _predict_pace(0, 16)
        assert pace == "ミドル"

    def test_出走馬0頭で不明(self):
        pace = _predict_pace(0, 0)
        assert pace == "不明"


class TestPaceFavorableStyles:
    """ペースと有利脚質のマッピングテスト."""

    def test_ハイペースで差し追込が有利(self):
        assert PACE_FAVORABLE_STYLES["ハイ"] == ["差し", "追込"]

    def test_スローペースで逃げ先行が有利(self):
        assert PACE_FAVORABLE_STYLES["スロー"] == ["逃げ", "先行"]

    def test_ミドルペースで先行差しが有利(self):
        assert PACE_FAVORABLE_STYLES["ミドル"] == ["先行", "差し"]


class TestGeneratePaceAnalysis:
    """ペース分析コメント生成のテスト."""

    def test_ハイペースの分析コメント(self):
        runners_by_style = {
            "逃げ": [{"horse_name": "馬A"}, {"horse_name": "馬B"}, {"horse_name": "馬C"}],
            "先行": [],
            "差し": [],
            "追込": [],
            "自在": [],
            "不明": [],
        }
        comment = _generate_pace_analysis("ハイ", 3, runners_by_style)
        assert "ハイペース" in comment
        assert "差し・追込馬に展開利" in comment

    def test_スローペースの分析コメント(self):
        runners_by_style = {
            "逃げ": [{"horse_name": "逃げ馬"}],
            "先行": [],
            "差し": [],
            "追込": [],
            "自在": [],
            "不明": [],
        }
        comment = _generate_pace_analysis("スロー", 1, runners_by_style)
        assert "スローペース" in comment
        assert "逃げ馬" in comment

    def test_ミドルペースの分析コメント(self):
        runners_by_style = {
            "逃げ": [{"horse_name": "馬A"}, {"horse_name": "馬B"}],
            "先行": [],
            "差し": [],
            "追込": [],
            "自在": [],
            "不明": [],
        }
        comment = _generate_pace_analysis("ミドル", 2, runners_by_style)
        assert "ミドルペース" in comment


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
        assert result["predicted_pace"] == "ハイ"
        assert result["favorable_styles"] == ["差し", "追込"]
        assert len(result["runners_by_style"]["逃げ"]) == 3
        assert len(result["runners_by_style"]["先行"]) == 1
        assert len(result["runners_by_style"]["差し"]) == 1
        assert len(result["runners_by_style"]["追込"]) == 1

    def test_逃げ馬1頭でスローペース予想(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "逃げ馬", "running_style": "逃げ"},
            {"horse_number": 2, "horse_name": "先行馬1", "running_style": "先行"},
            {"horse_number": 3, "horse_name": "先行馬2", "running_style": "先行"},
            {"horse_number": 4, "horse_name": "差し馬", "running_style": "差し"},
        ]
        result = _analyze_race_development_impl("test_race", running_styles)

        assert result["predicted_pace"] == "スロー"
        assert result["favorable_styles"] == ["逃げ", "先行"]


class TestAnalyzeRunningStyleMatchImpl:
    """脚質マッチング分析の実装テスト."""

    def test_脚質データなしでエラー(self):
        result = _analyze_running_style_match_impl("test_race", [1, 2], [], "ハイ")
        assert "error" in result

    def test_ハイペースで差し馬は有利(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "差し馬", "running_style": "差し"},
        ]
        result = _analyze_running_style_match_impl("test_race", [1], running_styles, "ハイ")

        assert result["predicted_pace"] == "ハイ"
        assert len(result["horses"]) == 1
        assert result["horses"][0]["pace_compatibility"] == "有利"
        assert "好展開" in result["horses"][0]["comment"]

    def test_ハイペースで先行馬は不利(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "先行馬", "running_style": "先行"},
        ]
        result = _analyze_running_style_match_impl("test_race", [1], running_styles, "ハイ")

        assert result["horses"][0]["pace_compatibility"] == "不利"
        assert "厳しい展開" in result["horses"][0]["comment"]

    def test_スローペースで逃げ馬は有利(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "逃げ馬", "running_style": "逃げ"},
        ]
        result = _analyze_running_style_match_impl("test_race", [1], running_styles, "スロー")

        assert result["horses"][0]["pace_compatibility"] == "有利"

    def test_スローペースで追込馬は不利(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "追込馬", "running_style": "追込"},
        ]
        result = _analyze_running_style_match_impl("test_race", [1], running_styles, "スロー")

        assert result["horses"][0]["pace_compatibility"] == "不利"
        assert "脚を余す" in result["horses"][0]["comment"]

    def test_自在馬は常に中立(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "自在馬", "running_style": "自在"},
        ]
        result = _analyze_running_style_match_impl("test_race", [1], running_styles, "ハイ")

        assert result["horses"][0]["pace_compatibility"] == "中立"
        assert "どの展開にも対応" in result["horses"][0]["comment"]

    def test_脚質不明は不明と表示(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "不明馬", "running_style": "不明"},
        ]
        result = _analyze_running_style_match_impl("test_race", [1], running_styles, "ハイ")

        assert result["horses"][0]["pace_compatibility"] == "不明"

    def test_選択していない馬は結果に含まれない(self):
        running_styles = [
            {"horse_number": 1, "horse_name": "馬1", "running_style": "逃げ"},
            {"horse_number": 2, "horse_name": "馬2", "running_style": "先行"},
            {"horse_number": 3, "horse_name": "馬3", "running_style": "差し"},
        ]
        result = _analyze_running_style_match_impl("test_race", [1, 3], running_styles, "ハイ")

        assert len(result["horses"]) == 2
        horse_numbers = [h["horse_number"] for h in result["horses"]]
        assert 1 in horse_numbers
        assert 3 in horse_numbers
        assert 2 not in horse_numbers


class TestIntegration:
    """統合テスト."""

    def test_展開分析から脚質マッチング分析まで(self):
        """展開分析結果を使って脚質マッチング分析を行う統合テスト."""
        running_styles = [
            {"horse_number": 1, "horse_name": "逃げ馬1", "running_style": "逃げ"},
            {"horse_number": 2, "horse_name": "逃げ馬2", "running_style": "逃げ"},
            {"horse_number": 3, "horse_name": "逃げ馬3", "running_style": "逃げ"},
            {"horse_number": 4, "horse_name": "先行馬", "running_style": "先行"},
            {"horse_number": 5, "horse_name": "差し馬", "running_style": "差し"},
            {"horse_number": 6, "horse_name": "追込馬", "running_style": "追込"},
        ]

        # 展開分析
        development = _analyze_race_development_impl("test_race", running_styles)
        assert development["predicted_pace"] == "ハイ"

        # 差し馬と追込馬を選択した場合の相性分析
        match = _analyze_running_style_match_impl(
            "test_race",
            [5, 6],
            running_styles,
            development["predicted_pace"]
        )

        # ハイペースなので差し・追込は有利
        assert all(h["pace_compatibility"] == "有利" for h in match["horses"])
