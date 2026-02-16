"""レース分析ツールのテスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.race_analyzer import _compute_weighted_probabilities, _analyze_race_impl


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
                    {"horse_number": 1, "score": 100},
                    {"horse_number": 2, "score": 80},
                    {"horse_number": 3, "score": 60},
                ],
            },
            {
                "source": "kichiuma",
                "predictions": [
                    {"horse_number": 1, "score": 90},
                    {"horse_number": 2, "score": 90},
                    {"horse_number": 3, "score": 60},
                ],
            },
            {
                "source": "daily",
                "predictions": [
                    {"horse_number": 1, "score": 80},
                    {"horse_number": 2, "score": 70},
                    {"horse_number": 3, "score": 50},
                ],
            },
        ],
    }


# =============================================================================
# 重み付き統合確率テスト
# =============================================================================


class TestComputeWeightedProbabilities:
    """重み付き統合確率の計算テスト."""

    def test_確率の合計が1になる(self):
        ai_result = _make_ai_result_multi_source()
        weights = {"jiro8": 0.4, "kichiuma": 0.35, "daily": 0.25}
        probs = _compute_weighted_probabilities(ai_result, weights)
        assert abs(sum(probs.values()) - 1.0) < 1e-9

    def test_重みが反映される(self):
        """jiro8の重みが高い → jiro8で1位のhorse1の確率が高くなる."""
        ai_result = _make_ai_result_multi_source()
        # jiro8偏重: horse1=100, horse2=80 → horse1有利
        heavy_jiro8 = {"jiro8": 0.8, "kichiuma": 0.1, "daily": 0.1}
        probs_heavy = _compute_weighted_probabilities(ai_result, heavy_jiro8)
        # kichiuma偏重: horse1=90, horse2=90 → horse1とhorse2が接近
        heavy_kichiuma = {"jiro8": 0.1, "kichiuma": 0.8, "daily": 0.1}
        probs_kichiuma = _compute_weighted_probabilities(ai_result, heavy_kichiuma)
        # jiro8偏重のほうがhorse1とhorse2の差が大きい
        gap_heavy = probs_heavy[1] - probs_heavy[2]
        gap_kichiuma = probs_kichiuma[1] - probs_kichiuma[2]
        assert gap_heavy > gap_kichiuma

    def test_ソースが1つしかない場合(self):
        ai_result = {
            "sources": [
                {
                    "source": "jiro8",
                    "predictions": [
                        {"horse_number": 1, "score": 100},
                        {"horse_number": 2, "score": 50},
                    ],
                },
            ],
        }
        weights = {"jiro8": 0.4, "kichiuma": 0.35, "daily": 0.25}
        probs = _compute_weighted_probabilities(ai_result, weights)
        assert len(probs) == 2
        assert abs(sum(probs.values()) - 1.0) < 1e-9

    def test_空のソースの場合(self):
        ai_result = {"sources": []}
        weights = {"jiro8": 0.4, "kichiuma": 0.35, "daily": 0.25}
        probs = _compute_weighted_probabilities(ai_result, weights)
        assert probs == {}

    def test_Decimal型のスコアに対応(self):
        from decimal import Decimal

        ai_result = {
            "sources": [
                {
                    "source": "jiro8",
                    "predictions": [
                        {"horse_number": 1, "score": Decimal("100")},
                        {"horse_number": 2, "score": Decimal("50")},
                    ],
                },
            ],
        }
        weights = {"jiro8": 0.4}
        probs = _compute_weighted_probabilities(ai_result, weights)
        assert isinstance(probs[1], float)


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
        assert "predicted_pace" in result["race_info"]
        assert "skip_score" in result["race_info"]
        assert "ai_consensus" in result["race_info"]
        assert "confidence_factor" in result["race_info"]

        # horses の検証
        assert len(result["horses"]) == 6
        horse1 = result["horses"][0]
        assert "number" in horse1
        assert "name" in horse1
        assert "odds" in horse1
        assert "base_win_probability" in horse1
        assert isinstance(horse1["base_win_probability"], float)

        # source_weights の検証
        assert "source_weights" in result

    def test_全馬のベース確率合計が1になる(self):
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        ai_result = {
            "sources": [
                {"source": "jiro8", "predictions": ai_preds},
            ],
        }

        result = _analyze_race_impl(
            race_id="202602010511",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=12,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=[],
        )

        total_prob = sum(h["base_win_probability"] for h in result["horses"])
        assert abs(total_prob - 1.0) < 1e-9

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
