"""レース分析ツールのテスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.race_analyzer import _analyze_race_impl


# =============================================================================
# テスト用データ
# =============================================================================


def _make_ai_result_multi_source() -> dict:
    """3ソースのAI予想結果を生成する."""
    return {
        "sources": [
            {
                "source": "jiro8",
                "predictions": [
                    {"horse_number": 1, "score": 100, "rank": 1},
                    {"horse_number": 2, "score": 80, "rank": 2},
                    {"horse_number": 3, "score": 60, "rank": 3},
                ],
            },
            {
                "source": "kichiuma",
                "predictions": [
                    {"horse_number": 1, "score": 90, "rank": 1},
                    {"horse_number": 2, "score": 90, "rank": 2},
                    {"horse_number": 3, "score": 60, "rank": 3},
                ],
            },
            {
                "source": "daily",
                "predictions": [
                    {"horse_number": 1, "score": 80, "rank": 1},
                    {"horse_number": 2, "score": 70, "rank": 2},
                    {"horse_number": 3, "score": 50, "rank": 3},
                ],
            },
        ],
        "consensus": {
            "agreed_top3": [1, 2],
            "consensus_level": "概ね合意",
            "divergence_horses": [],
        },
    }


# =============================================================================
# _analyze_race_impl 用テストデータ
# =============================================================================


def _make_runners(count: int, *, with_odds: bool = True) -> list[dict]:
    """テスト用出走馬データを生成する."""
    runners = []
    for i in range(1, count + 1):
        runner = {
            "horse_number": i,
            "horse_name": f"テスト馬{i}",
            "popularity": i,
        }
        if with_odds:
            runner["odds"] = round(2.0 + i * 1.5, 1)
        runners.append(runner)
    return runners


def _make_ai_predictions(count: int) -> list[dict]:
    """テスト用AI予想データを生成する."""
    preds = []
    for i in range(1, count + 1):
        preds.append({
            "horse_number": i,
            "horse_name": f"テスト馬{i}",
            "rank": i,
            "score": 400 - (i - 1) * 30,
        })
    return preds


def _make_running_styles(count: int) -> list[dict]:
    """テスト用脚質データを生成する."""
    styles = ["逃げ", "先行", "差し", "追込", "自在"]
    result = []
    for i in range(1, count + 1):
        result.append({
            "horse_number": i,
            "horse_name": f"テスト馬{i}",
            "running_style": styles[(i - 1) % len(styles)],
        })
    return result


# =============================================================================
# _analyze_race_impl テスト
# =============================================================================


class TestAnalyzeRaceImpl:
    """_analyze_race_impl のテスト."""

    def test_基本的なレース分析結果の構造(self):
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        ai_result = {
            "sources": [
                {"source": "jiro8", "predictions": ai_preds},
            ],
        }
        running_styles = _make_running_styles(6)

        result = _analyze_race_impl(
            race_id="202602010511",
            race_name="東京11R テスト重賞",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=6,
            race_conditions=["芝", "良"],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=running_styles,
        )

        # race_info の検証
        assert result["race_info"]["race_id"] == "202602010511"
        assert result["race_info"]["race_name"] == "東京11R テスト重賞"
        assert result["race_info"]["total_runners"] == 6
        assert "difficulty" in result["race_info"]
        assert "running_style_summary" in result["race_info"]
        assert "skip_score" in result["race_info"]
        assert "ai_consensus" in result["race_info"]
        assert "confidence_factor" in result["race_info"]

        # horses の検証
        assert len(result["horses"]) == 6
        horse1 = result["horses"][0]
        assert "number" in horse1
        assert "name" in horse1
        assert "odds" in horse1
        assert "ai_predictions" in horse1
        assert isinstance(horse1["ai_predictions"], dict)
        assert "running_style" in horse1
        assert "pace_compatibility" not in horse1

        # consensus の検証（1ソースの場合はNone）
        assert "consensus" in result["race_info"]

    def test_スピード指数と過去成績が含まれる(self):
        runners = _make_runners(3)
        ai_preds = _make_ai_predictions(3)
        ai_result = {"sources": [{"source": "jiro8", "predictions": ai_preds}]}

        speed_index_data = {
            "horses": [
                {"horse_number": 1, "indices": [{"value": 105}]},
                {"horse_number": 2, "indices": [{"value": 98}, {"value": 100}]},
            ]
        }
        past_performance_data = {
            "horses": [
                {"horse_number": 1, "performances": [
                    {"finish_position": 1}, {"finish_position": 3},
                ]},
            ]
        }

        result = _analyze_race_impl(
            race_id="test",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=3,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=[],
            speed_index_data=speed_index_data,
            past_performance_data=past_performance_data,
        )

        horse1 = next(h for h in result["horses"] if h["number"] == 1)
        assert horse1["speed_index"] is not None
        assert horse1["speed_index"]["latest"] == 105
        assert horse1["recent_form"] == [1, 3]

    def test_ai_predictionsにスコアと順位が含まれる(self):
        runners = _make_runners(3)
        ai_result = _make_ai_result_multi_source()

        result = _analyze_race_impl(
            race_id="test",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=3,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=[],
        )

        horse1 = next(h for h in result["horses"] if h["number"] == 1)
        ai_preds = horse1["ai_predictions"]

        # 3ソース分のデータがある
        assert "jiro8" in ai_preds
        assert "kichiuma" in ai_preds
        assert "daily" in ai_preds

        # 各ソースにscoreとrankがある
        assert ai_preds["jiro8"]["score"] == 100
        assert ai_preds["jiro8"]["rank"] == 1
        assert ai_preds["kichiuma"]["score"] == 90
        assert ai_preds["kichiuma"]["rank"] == 1
        assert ai_preds["daily"]["score"] == 80
        assert ai_preds["daily"]["rank"] == 1

        # 2番馬も確認
        horse2 = next(h for h in result["horses"] if h["number"] == 2)
        assert horse2["ai_predictions"]["jiro8"]["score"] == 80
        assert horse2["ai_predictions"]["jiro8"]["rank"] == 2

    def test_consensusがrace_infoに含まれる(self):
        runners = _make_runners(3)
        ai_result = _make_ai_result_multi_source()

        result = _analyze_race_impl(
            race_id="test",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=3,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=[],
        )

        consensus = result["race_info"]["consensus"]
        assert consensus is not None
        assert "consensus_level" in consensus
        assert consensus["consensus_level"] == "概ね合意"
        assert "agreed_top3" in consensus

    def test_1ソースの場合consensusはNone(self):
        runners = _make_runners(3)
        ai_preds = _make_ai_predictions(3)
        ai_result = {
            "sources": [{"source": "jiro8", "predictions": ai_preds}],
        }

        result = _analyze_race_impl(
            race_id="test",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=3,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=[],
        )

        assert result["race_info"]["consensus"] is None

    def test_running_style_summaryが正しく集計される(self):
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        ai_result = {"sources": [{"source": "jiro8", "predictions": ai_preds}]}
        running_styles = _make_running_styles(6)

        result = _analyze_race_impl(
            race_id="test",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=6,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=running_styles,
        )

        summary = result["race_info"]["running_style_summary"]
        # _make_running_styles: 逃げ, 先行, 差し, 追込, 自在, 逃げ の順
        assert summary["逃げ"] == 2
        assert summary["先行"] == 1
        assert summary["差し"] == 1
        assert summary["追込"] == 1
        assert summary["自在"] == 1

    def test_脚質データなしの場合running_style_summaryは空(self):
        runners = _make_runners(3)
        ai_preds = _make_ai_predictions(3)
        ai_result = {"sources": [{"source": "jiro8", "predictions": ai_preds}]}

        result = _analyze_race_impl(
            race_id="test",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=3,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=[],
        )

        assert result["race_info"]["running_style_summary"] == {}
