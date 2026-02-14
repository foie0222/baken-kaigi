"""レース分析ツールのテスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.race_analyzer import _compute_weighted_probabilities


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
        """jiro8の重みが高い -> jiro8で1位のhorse1の確率が高くなる."""
        ai_result = _make_ai_result_multi_source()
        # jiro8偏重: horse1=100, horse2=80 -> horse1有利
        heavy_jiro8 = {"jiro8": 0.8, "kichiuma": 0.1, "daily": 0.1}
        probs_heavy = _compute_weighted_probabilities(ai_result, heavy_jiro8)
        # kichiuma偏重: horse1=90, horse2=90 -> horse1とhorse2が接近
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
