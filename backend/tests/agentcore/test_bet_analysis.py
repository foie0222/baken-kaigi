"""買い目分析ツールのテスト."""

import sys
from pathlib import Path

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.bet_analysis import (
    _calculate_expected_value,
    _estimate_probability,
    _analyze_weaknesses,
    _calculate_torigami_risk,
    _analyze_bet_selection_impl,
    _calculate_combination_probability,
    _get_runners_correction,
    _get_race_condition_correction,
    _calculate_composite_odds,
    _analyze_ai_index_context,
    _optimize_fund_allocation,
    _identify_score_cluster,
)


class TestEstimateProbability:
    """確率推定のテスト."""

    def test_単勝1番人気の勝率は約33パーセント(self):
        prob = _estimate_probability(1, "win")
        assert prob == 0.33

    def test_単勝10番人気の勝率は約2パーセント(self):
        prob = _estimate_probability(10, "win")
        assert prob == 0.02

    def test_複勝1番人気の3着内率は約65パーセント(self):
        prob = _estimate_probability(1, "place")
        assert prob == 0.65

    def test_複勝5番人気の3着内率は約30パーセント(self):
        prob = _estimate_probability(5, "place")
        assert prob == 0.30

    def test_馬連1番人気の2着内率は約52パーセント(self):
        prob = _estimate_probability(1, "quinella")
        assert prob == 0.52

    def test_馬連5番人気の2着内率は約19パーセント(self):
        prob = _estimate_probability(5, "quinella")
        assert prob == 0.19

    def test_範囲外の人気は最低値を返す(self):
        prob = _estimate_probability(20, "win")
        assert prob == 0.002


class TestRunnersCorrection:
    """出走頭数補正のテスト."""

    def test_8頭立ての1番人気は補正が大きい(self):
        correction = _get_runners_correction(8, 1)
        assert correction == 1.25

    def test_18頭立ては補正なし(self):
        correction = _get_runners_correction(18, 1)
        assert correction == 1.0

    def test_12頭立ての1番人気は中程度の補正(self):
        correction = _get_runners_correction(12, 1)
        assert correction == 1.10


class TestRaceConditionCorrection:
    """レース条件補正のテスト."""

    def test_ハンデ戦は人気馬の信頼度が下がる(self):
        correction = _get_race_condition_correction(["handicap"])
        assert correction == 0.85

    def test_G1は堅い傾向(self):
        correction = _get_race_condition_correction(["g1"])
        assert correction == 1.05

    def test_条件なしは補正なし(self):
        correction = _get_race_condition_correction(None)
        assert correction == 1.0

    def test_複数条件は最も影響の大きいものを適用(self):
        correction = _get_race_condition_correction(["handicap", "hurdle"])
        assert correction == 0.80  # hurdle が最も大きい


class TestCalculateExpectedValue:
    """期待値計算のテスト."""

    def test_高オッズ低人気で妙味あり_単勝(self):
        # 10番人気（勝率2%）でオッズ100倍 → 期待値 2.0
        result = _calculate_expected_value(100.0, 10, "win")
        assert result["expected_return"] == 2.0
        assert result["value_rating"] == "妙味あり"

    def test_低オッズ高人気で割高_単勝(self):
        # 1番人気（勝率33%）でオッズ1.5倍 → 期待値 0.495
        result = _calculate_expected_value(1.5, 1, "win")
        assert result["expected_return"] == 0.49  # 1.5 * 0.33 = 0.495 → round(0.495, 2) = 0.49
        assert result["value_rating"] == "割高"

    def test_複勝の期待値計算(self):
        # 5番人気（3着内率30%）でオッズ3.5倍 → 期待値 1.05
        result = _calculate_expected_value(3.5, 5, "place")
        assert result["expected_return"] == 1.05
        assert result["value_rating"] == "適正"
        assert "3着内率" in result["probability_source"]

    def test_オッズ0の場合はデータ不足(self):
        result = _calculate_expected_value(0, 1, "win")
        assert result["value_rating"] == "データ不足"


class TestCalculateCombinationProbability:
    """組み合わせ確率のテスト."""

    def test_馬連の組み合わせ確率(self):
        result = _calculate_combination_probability([1, 2], "quinella")
        # 1番人気52% * 2番人気38% * 1.5補正
        assert result["probability"] > 0
        assert "2頭同時" in result["method"]

    def test_三連複の組み合わせ確率(self):
        result = _calculate_combination_probability([1, 2, 3], "trio")
        # 3着内率の積 * 2.0補正
        assert result["probability"] > 0
        assert "3頭同時" in result["method"]

    def test_馬番不足の場合(self):
        result = _calculate_combination_probability([1], "quinella")
        assert result["probability"] == 0
        assert "馬番不足" in result["method"]


class TestAnalyzeWeaknesses:
    """弱点分析のテスト."""

    def test_人気馬偏重で警告(self):
        horses = [
            {"horse_number": 1, "horse_name": "A", "popularity": 1, "odds": 2.0},
            {"horse_number": 2, "horse_name": "B", "popularity": 2, "odds": 4.0},
            {"horse_number": 3, "horse_name": "C", "popularity": 3, "odds": 6.0},
        ]
        weaknesses = _analyze_weaknesses(horses, "trio", 16)
        assert any("人気馬のみの選択" in w for w in weaknesses)
        assert any("トリガミ" in w for w in weaknesses)

    def test_穴馬偏重で警告(self):
        horses = [
            {"horse_number": 10, "horse_name": "X", "popularity": 10, "odds": 50.0},
            {"horse_number": 11, "horse_name": "Y", "popularity": 11, "odds": 80.0},
        ]
        weaknesses = _analyze_weaknesses(horses, "quinella", 16)
        assert any("穴馬のみの選択" in w for w in weaknesses)

    def test_最下位人気で警告(self):
        horses = [
            {"horse_number": 16, "horse_name": "最弱", "popularity": 16, "odds": 444.9},
        ]
        weaknesses = _analyze_weaknesses(horses, "win", 16)
        assert any("最下位人気" in w for w in weaknesses)

    def test_1番人気依存で警告(self):
        horses = [
            {"horse_number": 1, "horse_name": "A", "popularity": 1, "odds": 2.0},
            {"horse_number": 5, "horse_name": "B", "popularity": 5, "odds": 10.0},
        ]
        weaknesses = _analyze_weaknesses(horses, "quinella", 16)
        assert any("1番人気を軸" in w for w in weaknesses)

    def test_ハンデ戦で警告(self):
        horses = [
            {"horse_number": 1, "horse_name": "A", "popularity": 1, "odds": 2.0},
        ]
        weaknesses = _analyze_weaknesses(horses, "win", 16, race_conditions=["handicap"])
        assert any("ハンデ戦" in w for w in weaknesses)

    def test_少頭数で高オッズ馬の警告(self):
        horses = [
            {"horse_number": 8, "horse_name": "A", "popularity": 8, "odds": 30.0},
        ]
        weaknesses = _analyze_weaknesses(horses, "win", 8)
        assert any("少頭数" in w for w in weaknesses)


class TestCalculateTorigamiRisk:
    """トリガミリスク計算のテスト."""

    def test_単勝低オッズでトリガミリスク高(self):
        horses = [{"horse_number": 1, "odds": 1.2, "popularity": 1}]
        result = _calculate_torigami_risk("win", horses, 1000)
        assert result["risk_level"] == "高"
        assert result["is_torigami_likely"] is True

    def test_三連系人気馬のみでトリガミリスク高(self):
        horses = [
            {"horse_number": 1, "popularity": 1},
            {"horse_number": 2, "popularity": 2},
            {"horse_number": 3, "popularity": 3},
        ]
        result = _calculate_torigami_risk("trio", horses, 100)
        assert result["risk_level"] == "高"

    def test_穴馬混合でトリガミリスク低(self):
        horses = [
            {"horse_number": 1, "popularity": 1},
            {"horse_number": 8, "popularity": 8},
            {"horse_number": 12, "popularity": 12},
        ]
        result = _calculate_torigami_risk("trio", horses, 100)
        assert result["risk_level"] == "低"


class TestAnalyzeBetSelection:
    """買い目分析統合テスト."""

    def test_16番人気単勝の分析(self):
        """ユーザーが報告した実例のテスト."""
        runners = [{"horse_number": i, "horse_name": f"馬{i}", "popularity": i, "odds": i * 10.0} for i in range(1, 17)]
        runners[15]["odds"] = 444.9  # 16番人気のオッズを実例に合わせる

        result = _analyze_bet_selection_impl(
            race_id="test",
            bet_type="win",
            horse_numbers=[16],
            amount=100,
            runners_data=runners,
        )

        # 期待値分析が含まれていること
        assert "selected_horses" in result
        assert result["selected_horses"][0]["expected_value"]["estimated_probability"] == 0.3  # 0.3%
        assert result["selected_horses"][0]["expected_value"]["value_rating"] == "妙味あり"  # 444.9 * 0.003 = 1.33

        # 弱点分析が含まれていること
        assert "weaknesses" in result
        assert any("最下位人気" in w for w in result["weaknesses"])

    def test_人気馬三連複の分析(self):
        """人気馬中心の三連複のテスト."""
        runners = [{"horse_number": i, "horse_name": f"馬{i}", "popularity": i, "odds": i * 2.0} for i in range(1, 17)]

        result = _analyze_bet_selection_impl(
            race_id="test",
            bet_type="trio",
            horse_numbers=[1, 2, 3],
            amount=100,
            runners_data=runners,
        )

        # トリガミリスクが高いこと
        assert result["torigami_risk"]["risk_level"] == "高"

        # 弱点分析に人気馬偏重の警告があること
        assert any("人気馬のみ" in w for w in result["weaknesses"])

        # 組み合わせ確率が計算されていること
        assert "combination_probability" in result
        assert result["combination_probability"]["probability"] > 0

    def test_レース条件を渡せること(self):
        """レース条件を渡した場合のテスト."""
        runners = [{"horse_number": i, "horse_name": f"馬{i}", "popularity": i, "odds": i * 2.0} for i in range(1, 17)]

        result = _analyze_bet_selection_impl(
            race_id="test",
            bet_type="win",
            horse_numbers=[1],
            amount=100,
            runners_data=runners,
            race_conditions=["handicap"],
        )

        # レース条件が結果に含まれていること
        assert "race_conditions" in result
        assert "handicap" in result["race_conditions"]

        # ハンデ戦の警告があること
        assert any("ハンデ戦" in w for w in result["weaknesses"])

    def test_8頭立てでの分析(self):
        """少頭数での分析テスト."""
        runners = [{"horse_number": i, "horse_name": f"馬{i}", "popularity": i, "odds": i * 3.0} for i in range(1, 9)]

        result = _analyze_bet_selection_impl(
            race_id="test",
            bet_type="win",
            horse_numbers=[1],
            amount=100,
            runners_data=runners,
        )

        # 出走頭数が8であること
        assert result["total_runners"] == 8

        # 1番人気の確率が補正されていること（33% * 1.25 = 41.25%）
        prob = result["selected_horses"][0]["expected_value"]["estimated_probability"]
        assert prob > 33  # 補正により33%より高くなる

    def test_合成オッズが結果に含まれる(self):
        """合成オッズが分析結果に含まれることを確認."""
        runners = [{"horse_number": i, "horse_name": f"馬{i}", "popularity": i, "odds": i * 2.0} for i in range(1, 17)]

        result = _analyze_bet_selection_impl(
            race_id="test",
            bet_type="win",
            horse_numbers=[1, 2, 3],
            amount=300,
            runners_data=runners,
        )

        assert "composite_odds" in result
        assert result["composite_odds"]["composite_odds"] > 0

    def test_AI指数コンテキストが結果に含まれる(self):
        """AI指数を渡した場合にコンテキストが含まれることを確認."""
        runners = [{"horse_number": i, "horse_name": f"馬{i}", "popularity": i, "odds": i * 2.0} for i in range(1, 17)]
        ai_preds = [
            {"horse_number": 1, "horse_name": "馬1", "score": 350, "rank": 1},
            {"horse_number": 2, "horse_name": "馬2", "score": 280, "rank": 2},
            {"horse_number": 3, "horse_name": "馬3", "score": 200, "rank": 3},
        ]

        result = _analyze_bet_selection_impl(
            race_id="test",
            bet_type="win",
            horse_numbers=[1, 2],
            amount=200,
            runners_data=runners,
            ai_predictions=ai_preds,
        )

        assert "ai_index_context" in result
        assert len(result["ai_index_context"]) == 2
        assert result["ai_index_context"][0]["ai_rank"] == 1

    def test_資金配分が結果に含まれる(self):
        """資金配分最適化が結果に含まれることを確認."""
        runners = [{"horse_number": i, "horse_name": f"馬{i}", "popularity": i, "odds": i * 5.0} for i in range(1, 17)]

        result = _analyze_bet_selection_impl(
            race_id="test",
            bet_type="win",
            horse_numbers=[1, 3, 5],
            amount=3000,
            runners_data=runners,
        )

        assert "fund_allocation" in result


class TestCompositeOdds:
    """合成オッズ計算のテスト."""

    def test_2つのオッズで合成オッズ計算(self):
        # 1/2.0 + 1/4.0 = 0.5 + 0.25 = 0.75 → 合成オッズ = 1/0.75 = 1.33
        result = _calculate_composite_odds([2.0, 4.0])
        assert result["composite_odds"] == 1.33
        assert result["is_torigami"] is True
        assert result["torigami_warning"] is not None

    def test_高オッズでトリガミなし(self):
        # 1/10.0 + 1/20.0 = 0.1 + 0.05 = 0.15 → 合成オッズ = 1/0.15 = 6.67
        result = _calculate_composite_odds([10.0, 20.0])
        assert result["composite_odds"] == 6.67
        assert result["is_torigami"] is False
        assert result["torigami_warning"] is None

    def test_単一オッズは合成不要(self):
        result = _calculate_composite_odds([5.0])
        assert result["composite_odds"] == 5.0
        assert result["is_torigami"] is False

    def test_空リスト(self):
        result = _calculate_composite_odds([])
        assert result["composite_odds"] == 0
        assert result["bet_count"] == 0

    def test_ゼロオッズは除外(self):
        result = _calculate_composite_odds([0, 5.0, 10.0])
        assert result["bet_count"] == 2
        assert result["composite_odds"] > 0

    def test_境界値_合成オッズ2倍未満でトリガミ(self):
        # 1/3.0 + 1/3.0 = 0.667 → 合成オッズ = 1.5
        result = _calculate_composite_odds([3.0, 3.0])
        assert result["is_torigami"] is True

    def test_境界値_合成オッズ2倍以上はセーフ(self):
        # 1/5.0 + 1/5.0 = 0.4 → 合成オッズ = 2.5
        result = _calculate_composite_odds([5.0, 5.0])
        assert result["is_torigami"] is False


class TestAiIndexContext:
    """AI指数内訳コンテキストのテスト."""

    def test_AI予想なしは空リスト(self):
        result = _analyze_ai_index_context(None, [1, 2])
        assert result == []

    def test_AI1位の馬は最上位コメント(self):
        preds = [
            {"horse_number": 1, "horse_name": "馬1", "score": 400, "rank": 1},
            {"horse_number": 2, "horse_name": "馬2", "score": 300, "rank": 2},
            {"horse_number": 3, "horse_name": "馬3", "score": 200, "rank": 3},
        ]
        result = _analyze_ai_index_context(preds, [1])
        assert len(result) == 1
        assert result[0]["ai_rank"] == 1
        assert "最上位" in result[0]["gap_analysis"]
        assert result[0]["score_level"] == "非常に高い"

    def test_大差の場合は抜けた評価(self):
        preds = [
            {"horse_number": 1, "horse_name": "馬1", "score": 400, "rank": 1},
            {"horse_number": 2, "horse_name": "馬2", "score": 300, "rank": 2},
        ]
        result = _analyze_ai_index_context(preds, [1])
        assert "抜けた評価" in result[0]["gap_analysis"]

    def test_僅差の場合は僅差コメント(self):
        preds = [
            {"horse_number": 1, "horse_name": "馬1", "score": 310, "rank": 1},
            {"horse_number": 2, "horse_name": "馬2", "score": 300, "rank": 2},
        ]
        result = _analyze_ai_index_context(preds, [1])
        assert "僅差" in result[0]["gap_analysis"]

    def test_下位馬のコンテキスト(self):
        preds = [
            {"horse_number": 1, "horse_name": "馬1", "score": 400, "rank": 1},
            {"horse_number": 5, "horse_name": "馬5", "score": 150, "rank": 5},
            {"horse_number": 10, "horse_name": "馬10", "score": 50, "rank": 10},
        ]
        result = _analyze_ai_index_context(preds, [10])
        assert len(result) == 1
        assert result[0]["ai_rank"] == 10
        assert "低評価" in result[0]["gap_analysis"]

    def test_スコアレベル判定(self):
        preds = [
            {"horse_number": 1, "horse_name": "A", "score": 400, "rank": 1},
            {"horse_number": 2, "horse_name": "B", "score": 250, "rank": 2},
            {"horse_number": 3, "horse_name": "C", "score": 150, "rank": 3},
            {"horse_number": 4, "horse_name": "D", "score": 80, "rank": 4},
            {"horse_number": 5, "horse_name": "E", "score": 30, "rank": 5},
        ]
        result = _analyze_ai_index_context(preds, [1, 2, 3, 4, 5])
        levels = {r["horse_number"]: r["score_level"] for r in result}
        assert levels[1] == "非常に高い"
        assert levels[2] == "高い"
        assert levels[3] == "中程度"
        assert levels[4] == "低い"
        assert levels[5] == "非常に低い"


class TestIdentifyScoreCluster:
    """スコアクラスター識別のテスト."""

    def test_上位集団に属する場合(self):
        scores = [400, 380, 370, 200, 180, 100]
        cluster = _identify_score_cluster(scores, 380)
        assert "上位集団" in cluster

    def test_下位集団に属する場合(self):
        scores = [400, 380, 370, 200, 180, 50, 40]
        cluster = _identify_score_cluster(scores, 40)
        assert "下位集団" in cluster

    def test_少頭数の場合(self):
        scores = [300, 200]
        cluster = _identify_score_cluster(scores, 300)
        assert "少頭数" in cluster

    def test_空リスト(self):
        cluster = _identify_score_cluster([], 100)
        assert cluster == "不明"


class TestOptimizeFundAllocation:
    """資金配分最適化のテスト."""

    def test_期待値の高い馬に多く配分(self):
        horses = [
            {"horse_number": 1, "horse_name": "A", "odds": 5.0, "popularity": 3},
            {"horse_number": 2, "horse_name": "B", "odds": 50.0, "popularity": 10},
        ]
        result = _optimize_fund_allocation(horses, 2000, "win")
        assert len(result["allocations"]) == 2
        # 10番人気オッズ50倍は期待値高い（0.02 * 50 = 1.0）ので配分多め
        allocs = {a["horse_number"]: a for a in result["allocations"]}
        assert allocs[2]["suggested_amount"] >= 100

    def test_単一買い目は資金配分不要(self):
        horses = [{"horse_number": 1, "horse_name": "A", "odds": 3.0, "popularity": 1}]
        result = _optimize_fund_allocation(horses, 1000, "win")
        assert "不要" in result["strategy"]

    def test_三連系は資金配分対象外(self):
        horses = [
            {"horse_number": 1, "horse_name": "A", "odds": 3.0, "popularity": 1},
            {"horse_number": 2, "horse_name": "B", "odds": 5.0, "popularity": 2},
        ]
        result = _optimize_fund_allocation(horses, 1000, "trio")
        assert "不要" in result["strategy"]

    def test_100円単位に丸められる(self):
        horses = [
            {"horse_number": 1, "horse_name": "A", "odds": 5.0, "popularity": 3},
            {"horse_number": 2, "horse_name": "B", "odds": 10.0, "popularity": 5},
        ]
        result = _optimize_fund_allocation(horses, 1000, "win")
        for alloc in result["allocations"]:
            assert alloc["suggested_amount"] % 100 == 0

    def test_予算0は空結果(self):
        horses = [{"horse_number": 1, "horse_name": "A", "odds": 3.0, "popularity": 1}]
        result = _optimize_fund_allocation(horses, 0, "win")
        assert result["strategy"] == "データ不足"
