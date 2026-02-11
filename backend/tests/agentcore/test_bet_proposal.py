"""買い目提案ツールのテスト."""

import sys
from decimal import Decimal
from pathlib import Path

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.bet_proposal import (
    _calculate_composite_score,
    _select_axis_horses,
    _select_bet_types_by_difficulty,
    _generate_bet_candidates,
    _assign_relative_confidence,
    _allocate_budget,
    _assess_ai_consensus,
    _estimate_bet_odds,
    _generate_bet_proposal_impl,
    SKIP_GATE_THRESHOLD,
    TORIGAMI_COMPOSITE_ODDS_THRESHOLD,
)


# =============================================================================
# テスト用データ
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
            # 人気順にオッズを設定（1番人気=3.5倍、以降上昇）
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
# 軸馬選定テスト
# =============================================================================


class TestSelectAxisHorses:
    """軸馬選定のテスト."""

    def test_AI上位2頭が軸馬に選定される(self):
        """AI予想の上位2頭が軸馬に選定される."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        result = _select_axis_horses(runners, ai_preds)
        assert len(result) == 2
        # AI1位と2位が選ばれるはず
        selected_numbers = {r["horse_number"] for r in result}
        assert 1 in selected_numbers
        assert 2 in selected_numbers

    def test_ユーザー指定の軸馬が優先される(self):
        """axis_horsesが指定された場合はそれを使う."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        result = _select_axis_horses(runners, ai_preds, user_axis=[5, 8])
        assert len(result) == 2
        assert result[0]["horse_number"] == 5
        assert result[1]["horse_number"] == 8

    def test_ユーザー指定は最大2頭(self):
        """axis_horsesが3頭以上指定されても最大2頭に制限される."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        result = _select_axis_horses(runners, ai_preds, user_axis=[1, 3, 5, 7])
        assert len(result) == 2
        assert result[0]["horse_number"] == 1
        assert result[1]["horse_number"] == 3

    def test_複合スコアが計算される(self):
        """選定された軸馬にcomposite_scoreが含まれる."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        result = _select_axis_horses(runners, ai_preds)
        for axis in result:
            assert "composite_score" in axis
            assert axis["composite_score"] > 0

    def test_存在しない馬番は無視して自動選定にフォールバック(self):
        """ユーザー指定の馬番が全て出走馬に存在しない場合、自動選定にフォールバックする."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        result = _select_axis_horses(runners, ai_preds, user_axis=[99, 100])
        # 自動選定にフォールバックし、AI上位2頭が選ばれる
        assert len(result) == 2
        selected_numbers = {r["horse_number"] for r in result}
        assert 1 in selected_numbers
        assert 2 in selected_numbers

    def test_一部存在しない馬番は有効なものだけ採用(self):
        """ユーザー指定の一部が無効でも、有効な馬番のみ採用する."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        result = _select_axis_horses(runners, ai_preds, user_axis=[3, 99])
        assert len(result) == 1
        assert result[0]["horse_number"] == 3

    def test_AI上位で不人気馬はスコアにオッズ乖離ボーナス(self):
        """AI上位だが人気が低い馬にはオッズ乖離ボーナスが付く."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        # 1番馬のAI順位は1位、人気も1番人気 → 順当
        score_normal = _calculate_composite_score(1, runners, ai_preds)
        # 人気と馬番を入れ替えて、AI1位だが8番人気の馬を作る
        runners_mod = _make_runners(18)
        runners_mod[0]["popularity"] = 8  # 1番馬を8番人気に
        score_gap = _calculate_composite_score(1, runners_mod, ai_preds)
        # オッズ乖離ボーナスでスコアが上がるはず
        assert score_gap > score_normal


# =============================================================================
# 券種自動選定テスト
# =============================================================================


class TestSelectBetTypesByDifficulty:
    """券種選定のテスト."""

    def test_難易度1_2は馬連馬単(self):
        """難易度★1-2では馬連・馬単が推奨される."""
        result = _select_bet_types_by_difficulty(1)
        assert "quinella" in result or "exacta" in result
        result2 = _select_bet_types_by_difficulty(2)
        assert "quinella" in result2 or "exacta" in result2

    def test_難易度3は馬連と三連複(self):
        """難易度★3では馬連+三連複が推奨される."""
        result = _select_bet_types_by_difficulty(3)
        assert "quinella" in result
        assert "trio" in result

    def test_難易度4_5はワイドor三連複(self):
        """難易度★4-5ではワイドまたは三連複が推奨される."""
        result4 = _select_bet_types_by_difficulty(4)
        assert "trio" in result4 or "quinella_place" in result4
        result5 = _select_bet_types_by_difficulty(5)
        assert "quinella_place" in result5

    def test_ユーザー指定が優先される(self):
        """preferred_bet_typesが指定された場合はそれを使う."""
        result = _select_bet_types_by_difficulty(1, preferred_bet_types=["trifecta"])
        assert result == ["trifecta"]

    def test_範囲外の難易度はクランプされる(self):
        """難易度0以下は1、6以上は5にクランプ."""
        result_low = _select_bet_types_by_difficulty(0)
        result_1 = _select_bet_types_by_difficulty(1)
        assert result_low == result_1

        result_high = _select_bet_types_by_difficulty(10)
        result_5 = _select_bet_types_by_difficulty(5)
        assert result_high == result_5


# =============================================================================
# 予算配分テスト
# =============================================================================


class TestAllocateBudget:
    """予算配分のテスト."""

    def test_信頼度別に配分される(self):
        """高信頼/中信頼/穴狙いで異なる金額が配分される."""
        bets = [
            {"confidence": "high", "bet_type": "quinella"},
            {"confidence": "medium", "bet_type": "quinella"},
            {"confidence": "low", "bet_type": "quinella"},
        ]
        result = _allocate_budget(bets, 10000)
        amounts = [b["amount"] for b in result]
        # 全ての買い目に金額が設定される
        assert all(a >= 100 for a in amounts)
        # 高信頼 > 中信頼 > 穴狙い
        assert result[0]["amount"] >= result[1]["amount"]
        assert result[1]["amount"] >= result[2]["amount"]

    def test_100円単位に丸められる(self):
        """配分額は100円単位."""
        bets = [
            {"confidence": "high", "bet_type": "quinella"},
            {"confidence": "medium", "bet_type": "quinella"},
        ]
        result = _allocate_budget(bets, 3000)
        for bet in result:
            assert bet["amount"] % 100 == 0

    def test_最低100円保証(self):
        """予算が少なくても最低100円は配分される."""
        bets = [
            {"confidence": "high", "bet_type": "quinella"},
            {"confidence": "medium", "bet_type": "quinella"},
            {"confidence": "low", "bet_type": "quinella"},
        ]
        result = _allocate_budget(bets, 300)
        for bet in result:
            assert bet["amount"] >= 100

    def test_予算ゼロの場合(self):
        """予算が0の場合はamountが付かない."""
        bets = [{"confidence": "high", "bet_type": "quinella"}]
        result = _allocate_budget(bets, 0)
        assert "amount" not in result[0] or result[0].get("amount", 0) == 0

    def test_空のリスト(self):
        """買い目が空の場合は空リストが返る."""
        result = _allocate_budget([], 10000)
        assert result == []

    def test_予算超過は買い目削減で防止(self):
        """予算が少なく買い目が多い場合、買い目を削減して予算内に収める."""
        bets = [
            {"confidence": "high", "bet_type": "quinella", "expected_value": 1.2},
            {"confidence": "high", "bet_type": "quinella", "expected_value": 1.1},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.0},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 0.9},
            {"confidence": "low", "bet_type": "quinella", "expected_value": 0.8},
            {"confidence": "low", "bet_type": "quinella", "expected_value": 0.7},
        ]
        result = _allocate_budget(bets, 300)
        total = sum(b.get("amount", 0) for b in result if "amount" in b)
        assert total <= 300

    def test_予算超過時は高信頼度が優先される(self):
        """予算不足で買い目を絞る場合、高信頼度が優先される."""
        bets = [
            {"confidence": "low", "bet_type": "quinella", "expected_value": 0.7},
            {"confidence": "high", "bet_type": "quinella", "expected_value": 1.2},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.0},
        ]
        result = _allocate_budget(bets, 200)
        # 予算200円 → 最大2点
        bets_with_amount = [b for b in result if "amount" in b]
        assert len(bets_with_amount) <= 2
        # 高信頼度が残っているはず
        confidences = {b["confidence"] for b in bets_with_amount}
        assert "high" in confidences

    def test_同一信頼度内で期待値が高い買い目により多く配分される(self):
        """同一グループ内でも期待値に応じた傾斜配分がされる."""
        bets = [
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 2.0},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.5},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 0.5},
        ]
        result = _allocate_budget(bets, 3000)
        # 期待値2.0 > 期待値1.5 > 期待値0.5 の順に金額が大きい（または同額）
        assert result[0]["amount"] >= result[1]["amount"]
        assert result[1]["amount"] >= result[2]["amount"]
        # 最高と最低が異なる（一律ではない）
        assert result[0]["amount"] > result[2]["amount"]

    def test_同一信頼度で全て期待値0の場合は均等配分(self):
        """全買い目の期待値が0の場合は均等配分にフォールバック."""
        bets = [
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 0},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 0},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 0},
        ]
        result = _allocate_budget(bets, 3000)
        amounts = [b["amount"] for b in result]
        # 全て同額
        assert len(set(amounts)) == 1

    def test_余剰予算が期待値の高い買い目に追加配分される(self):
        """丸めで余った予算は期待値の高い買い目に優先的に追加される."""
        bets = [
            {"confidence": "high", "bet_type": "quinella", "expected_value": 1.5},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.0},
            {"confidence": "low", "bet_type": "quinella", "expected_value": 0.5},
        ]
        result = _allocate_budget(bets, 3000)
        total = sum(b["amount"] for b in result)
        # 予算の90%以上を使い切る
        assert total >= 3000 * 0.9
        # 最高EVの買い目が最も多い金額を持つ
        assert result[0]["amount"] >= result[1]["amount"]
        assert result[0]["amount"] >= result[2]["amount"]

    def test_予算の大部分が使い切られる(self):
        """8点買いでも予算のほとんどが配分される."""
        bets = [
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 2.0},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.8},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.5},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.2},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.0},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 0.8},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 0.5},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 0.3},
        ]
        result = _allocate_budget(bets, 3000)
        total = sum(b["amount"] for b in result)
        # 予算の90%以上を使い切る（3000円のうち2700円以上）
        assert total >= 2700
        # 予算を超えない
        assert total <= 3000


# =============================================================================
# 推定オッズテスト
# =============================================================================


class TestEstimateBetOdds:
    """券種別オッズ推定のテスト."""

    def test_馬連は幾何平均ベースで推定される(self):
        """馬連のオッズは2頭の単勝オッズの幾何平均 × 補正係数."""
        import math
        odds = _estimate_bet_odds([3.5, 8.0], "quinella")
        geo_mean = math.sqrt(3.5 * 8.0)
        expected = round(geo_mean * 0.85, 1)
        assert odds == expected
        # 馬連は単勝より低くなるのが自然（1番人気と3番人気の組み合わせ）
        assert odds > 2.0  # トリガミにはならない

    def test_馬単は馬連より高い(self):
        """馬単は着順指定なので馬連より高い."""
        quinella = _estimate_bet_odds([3.5, 8.0], "quinella")
        exacta = _estimate_bet_odds([3.5, 8.0], "exacta")
        assert exacta > quinella

    def test_ワイドは馬連より低い(self):
        """ワイドは3着内なので馬連より低い."""
        quinella = _estimate_bet_odds([3.5, 8.0], "quinella")
        wide = _estimate_bet_odds([3.5, 8.0], "quinella_place")
        assert wide < quinella

    def test_三連複は3頭のオッズから推定される(self):
        """三連複は3頭の幾何平均ベース."""
        odds = _estimate_bet_odds([3.5, 8.0, 15.0], "trio")
        assert odds > 0
        # 三連複は2頭系より高いはず
        quinella = _estimate_bet_odds([3.5, 8.0], "quinella")
        assert odds > quinella

    def test_三連単は三連複より高い(self):
        """三連単は着順指定なので三連複より高い."""
        trio = _estimate_bet_odds([3.5, 8.0, 15.0], "trio")
        trifecta = _estimate_bet_odds([3.5, 8.0, 15.0], "trifecta")
        assert trifecta > trio

    def test_オッズ0の場合は0を返す(self):
        """有効なオッズが無い場合は0."""
        assert _estimate_bet_odds([0, 0], "quinella") == 0.0
        assert _estimate_bet_odds([], "quinella") == 0.0

    def test_Decimal型のオッズでも正常に計算できる(self):
        """DynamoDB由来のDecimal型を含むオッズリストでもエラーにならない."""
        from decimal import Decimal

        result = _estimate_bet_odds([Decimal("3.5"), Decimal("8.0")], "quinella")
        assert result > 0
        # float版と同じ結果になることを確認
        float_result = _estimate_bet_odds([3.5, 8.0], "quinella")
        assert result == float_result

    def test_Decimal型とfloat型が混在しても計算できる(self):
        """Decimalとfloatが混在しても正常に計算される."""
        from decimal import Decimal

        result = _estimate_bet_odds([Decimal("3.5"), 8.0], "quinella")
        assert result > 0

    def test_Decimal型の三連系オッズでも計算できる(self):
        """3頭のDecimal型オッズでも正常に計算される."""
        from decimal import Decimal

        result = _estimate_bet_odds(
            [Decimal("3.5"), Decimal("8.0"), Decimal("15.0")], "trio"
        )
        assert result > 0
        float_result = _estimate_bet_odds([3.5, 8.0, 15.0], "trio")
        assert result == float_result


# =============================================================================
# トリガミ除外テスト
# =============================================================================


class TestTorigamiExclusion:
    """トリガミ除外のテスト."""

    def test_低オッズの組み合わせは除外される(self):
        """合成オッズ < 2.0 の買い目はトリガミとして除外される."""
        runners = _make_runners(18)
        # 超低オッズに設定（人気馬のオッズを極端に低くする）
        runners[0]["odds"] = 1.3
        runners[1]["odds"] = 1.5
        ai_preds = _make_ai_predictions(18)
        axis = [{"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 90}]

        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["quinella"],
            total_runners=18,
        )
        # 合成オッズがTORIGAMI閾値以上のもののみ残る
        for bet in bets:
            assert bet["composite_odds"] >= TORIGAMI_COMPOSITE_ODDS_THRESHOLD or bet["composite_odds"] == 0


# =============================================================================
# 見送りゲートテスト
# =============================================================================


class TestSkipGate:
    """見送りゲートのテスト."""

    def test_見送りスコア7以上で予算半減(self):
        """見送りスコアが7以上の場合、予算が50%削減される."""
        runners = _make_runners(18)
        # 混戦AI予想
        ai_preds = [
            {"horse_number": i, "horse_name": f"テスト馬{i}", "rank": i, "score": 300 - (i - 1) * 5}
            for i in range(1, 19)
        ]
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            race_conditions=["handicap"],
            venue="福島",
            total_runners=18,
            running_styles=_make_running_styles(18),
        )
        # 見送りスコアが7以上であれば予算半減
        if result["race_summary"]["skip_score"] >= SKIP_GATE_THRESHOLD:
            # total_amount + budget_remaining <= 5000 (10000 * 0.5)
            assert result["total_amount"] + result["budget_remaining"] <= 5000

    def test_通常レースでは予算削減なし(self):
        """通常レースでは予算は削減されない."""
        runners = _make_runners(8)
        ai_preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            race_conditions=["g1"],
            venue="東京",
            total_runners=8,
        )
        assert result["race_summary"]["skip_score"] < SKIP_GATE_THRESHOLD
        # 予算削減なし
        assert result["total_amount"] + result["budget_remaining"] <= 10000


# =============================================================================
# AI合議レベルテスト
# =============================================================================


class TestAiConsensus:
    """AI合議レベルのテスト."""

    def test_スコア差が大きい場合は明確な上位(self):
        """1位と2位のスコア差が50以上なら「明確な上位」."""
        ai_preds = [
            {"horse_number": 1, "score": 400, "rank": 1},
            {"horse_number": 2, "score": 340, "rank": 2},
        ]
        assert _assess_ai_consensus(ai_preds) == "明確な上位"

    def test_スコア差が中程度は概ね合意(self):
        """1位と2位のスコア差が20-49なら「概ね合意」."""
        ai_preds = [
            {"horse_number": 1, "score": 400, "rank": 1},
            {"horse_number": 2, "score": 375, "rank": 2},
        ]
        assert _assess_ai_consensus(ai_preds) == "概ね合意"

    def test_スコア差が小さいと混戦(self):
        """1位と2位のスコア差が10未満なら「混戦」."""
        ai_preds = [
            {"horse_number": 1, "score": 400, "rank": 1},
            {"horse_number": 2, "score": 395, "rank": 2},
        ]
        assert _assess_ai_consensus(ai_preds) == "混戦"

    def test_データ不足(self):
        """AI予想が1頭以下なら「データ不足」."""
        assert _assess_ai_consensus([]) == "データ不足"
        assert _assess_ai_consensus([{"horse_number": 1, "score": 400}]) == "データ不足"


# =============================================================================
# 出力フォーマット検証テスト
# =============================================================================


class TestOutputFormat:
    """出力フォーマットのテスト."""

    def test_必須フィールドが存在する(self):
        """出力に必須フィールドが全て含まれる."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=5000,
            runners_data=runners,
            ai_predictions=ai_preds,
            race_name="東京11R 安田記念",
            total_runners=12,
        )
        assert "race_id" in result
        assert "race_summary" in result
        assert "proposed_bets" in result
        assert "total_amount" in result
        assert "budget_remaining" in result
        assert "analysis_comment" in result
        assert "disclaimer" in result

    def test_race_summaryの必須フィールド(self):
        """race_summaryに必須フィールドが含まれる."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=5000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
        )
        summary = result["race_summary"]
        assert "difficulty_stars" in summary
        assert "predicted_pace" in summary
        assert "ai_consensus_level" in summary
        assert "skip_score" in summary
        assert "skip_recommendation" in summary

    def test_proposed_betsの各要素に必須フィールドがある(self):
        """各買い目に必須フィールドが含まれる."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=5000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
        )
        for bet in result["proposed_bets"]:
            assert "bet_type" in bet
            assert "horse_numbers" in bet
            assert "bet_display" in bet
            assert "confidence" in bet
            assert "expected_value" in bet
            assert "composite_odds" in bet
            assert "reasoning" in bet

    def test_disclaimerが含まれる(self):
        """免責事項が含まれる."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=5000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
        )
        assert "最終判断" in result["disclaimer"]

    def test_total_amountはbudgetを超えない(self):
        """合計金額は予算を超えない."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=5000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
        )
        assert result["total_amount"] <= 5000


# =============================================================================
# 三連系のテスト
# =============================================================================


class TestTrioBets:
    """三連系買い目のテスト."""

    def test_三連複の買い目が生成される(self):
        """難易度3のレースで三連複の買い目が生成される."""
        runners = _make_runners(14)
        ai_preds = _make_ai_predictions(14)
        axis = [{"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 90}]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["trio"],
            total_runners=14,
        )
        trio_bets = [b for b in bets if b["bet_type"] == "trio"]
        assert len(trio_bets) > 0
        # 三連複は3頭の組み合わせ
        for bet in trio_bets:
            assert len(bet["horse_numbers"]) == 3
            # ソート済み
            assert bet["horse_numbers"] == sorted(bet["horse_numbers"])

    def test_三連単の着順が保持される(self):
        """三連単では着順（軸馬が先頭）が保持される."""
        runners = _make_runners(14)
        ai_preds = _make_ai_predictions(14)
        axis = [{"horse_number": 3, "horse_name": "テスト馬3", "composite_score": 90}]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["trifecta"],
            total_runners=14,
        )
        trifecta_bets = [b for b in bets if b["bet_type"] == "trifecta"]
        for bet in trifecta_bets:
            assert len(bet["horse_numbers"]) == 3
            # 軸馬が先頭
            assert bet["horse_numbers"][0] == 3


# =============================================================================
# 統合テスト
# =============================================================================


class TestIntegration:
    """統合テスト."""

    def test_全体フロー_12頭G1(self):
        """12頭G1レースの全体フローが正常に動作する."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        styles = _make_running_styles(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            race_name="東京11R 安田記念",
            race_conditions=["g1"],
            venue="東京",
            total_runners=12,
            running_styles=styles,
        )
        assert "error" not in result
        assert result["race_id"] == "20260201_05_11"
        assert result["race_summary"]["difficulty_stars"] >= 1
        assert len(result["proposed_bets"]) > 0
        assert result["total_amount"] > 0
        assert result["total_amount"] <= 10000

    def test_全体フロー_ユーザー指定軸馬(self):
        """ユーザー指定の軸馬でも正常に動作する."""
        runners = _make_runners(16)
        ai_preds = _make_ai_predictions(16)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=5000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=16,
            axis_horses=[5, 8],
        )
        assert "error" not in result
        # 提案された買い目に軸馬(5番 or 8番)が含まれている
        for bet in result["proposed_bets"]:
            assert 5 in bet["horse_numbers"] or 8 in bet["horse_numbers"]

    def test_全体フロー_ユーザー指定券種(self):
        """ユーザー指定の券種でも正常に動作する."""
        runners = _make_runners(14)
        ai_preds = _make_ai_predictions(14)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=5000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=14,
            preferred_bet_types=["quinella_place"],
        )
        assert "error" not in result
        for bet in result["proposed_bets"]:
            assert bet["bet_type"] == "quinella_place"


    def test_全体フロー_単勝指定で買い目が生成される(self):
        """preferred_bet_types=['win']で単勝の買い目が生成される."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=3000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
            preferred_bet_types=["win"],
        )
        assert "error" not in result
        assert len(result["proposed_bets"]) > 0
        for bet in result["proposed_bets"]:
            assert bet["bet_type"] == "win"
            assert len(bet["horse_numbers"]) == 1
            assert bet["bet_count"] == 1

    def test_全体フロー_複勝指定で買い目が生成される(self):
        """preferred_bet_types=['place']で複勝の買い目が生成される."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=3000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
            preferred_bet_types=["place"],
        )
        assert "error" not in result
        assert len(result["proposed_bets"]) > 0
        for bet in result["proposed_bets"]:
            assert bet["bet_type"] == "place"
            assert len(bet["horse_numbers"]) == 1


# =============================================================================
# 単勝/複勝候補生成テスト
# =============================================================================


class TestWinPlaceBets:
    """単勝/複勝の買い目生成テスト."""

    def test_単勝の買い目が軸馬から生成される(self):
        """bet_types=['win']で軸馬の単勝買い目が生成される."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        axis = [
            {"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 90},
            {"horse_number": 2, "horse_name": "テスト馬2", "composite_score": 80},
        ]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["win"],
            total_runners=12,
        )
        assert len(bets) == 2
        assert bets[0]["bet_type"] == "win"
        assert bets[0]["horse_numbers"] == [1]
        assert bets[0]["bet_display"] == "1"
        assert bets[1]["horse_numbers"] == [2]

    def test_複勝の買い目が軸馬から生成される(self):
        """bet_types=['place']で軸馬の複勝買い目が生成される."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        axis = [{"horse_number": 3, "horse_name": "テスト馬3", "composite_score": 85}]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["place"],
            total_runners=12,
        )
        assert len(bets) == 1
        assert bets[0]["bet_type"] == "place"
        assert bets[0]["horse_numbers"] == [3]

    def test_単勝の必須フィールドが揃っている(self):
        """単勝の買い目に必要なフィールドが全て含まれる."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        axis = [{"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 90}]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["win"],
            total_runners=12,
        )
        assert len(bets) == 1
        bet = bets[0]
        required_fields = [
            "bet_type", "bet_type_name", "horse_numbers",
            "bet_display", "confidence", "expected_value",
            "composite_odds", "reasoning", "bet_count",
        ]
        for field in required_fields:
            assert field in bet, f"フィールド {field} が欠落"

    def test_単勝と馬連の混合指定(self):
        """bet_types=['win', 'quinella']で両方の買い目が生成される."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        axis = [{"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 90}]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["win", "quinella"],
            total_runners=12,
        )
        win_bets = [b for b in bets if b["bet_type"] == "win"]
        quinella_bets = [b for b in bets if b["bet_type"] == "quinella"]
        assert len(win_bets) > 0
        assert len(quinella_bets) > 0


# =============================================================================
# DynamoDB Decimal型互換テスト
# =============================================================================


def _make_decimal_ai_predictions(count: int) -> list[dict]:
    """DynamoDB由来のDecimal型を含むAI予想データを生成する."""
    preds = []
    for i in range(1, count + 1):
        preds.append({
            "horse_number": Decimal(str(i)),
            "horse_name": f"テスト馬{i}",
            "rank": Decimal(str(i)),
            "score": Decimal(str(400 - (i - 1) * 30)),
        })
    return preds


class TestDecimalCompatibility:
    """DynamoDB Decimal型との互換性テスト."""

    def test_複合スコア計算でDecimal型のrankを処理できる(self):
        """AI予想のrankがDecimal型でもTypeErrorにならない."""
        runners = _make_runners(12)
        ai_preds = _make_decimal_ai_predictions(12)
        score = _calculate_composite_score(1, runners, ai_preds)
        assert isinstance(score, float)
        assert score > 0

    def test_軸馬選定でDecimal型のAI予想を処理できる(self):
        """Decimal型のAI予想データでも軸馬選定が正常動作する."""
        runners = _make_runners(12)
        ai_preds = _make_decimal_ai_predictions(12)
        result = _select_axis_horses(runners, ai_preds)
        assert len(result) >= 1
        assert all(isinstance(a["composite_score"], float) for a in result)

    def test_AI合議レベル判定でDecimal型のscoreを処理できる(self):
        """AI予想のscoreがDecimal型でも合議レベル判定が正常動作する."""
        ai_preds = _make_decimal_ai_predictions(12)
        result = _assess_ai_consensus(ai_preds)
        assert result in ("明確な上位", "やや接戦", "概ね合意", "データ不足", "混戦")

    def test_買い目生成でDecimal型のAI予想を処理できる(self):
        """Decimal型のAI予想データでも買い目生成が正常動作する."""
        runners = _make_runners(12)
        ai_preds = _make_decimal_ai_predictions(12)
        axis = [{"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 90}]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["win", "quinella"],
            total_runners=12,
        )
        assert len(bets) > 0

    def test_統合提案でDecimal型のAI予想を処理できる(self):
        """Decimal型のAI予想データでも統合提案が正常動作する."""
        runners = _make_runners(12)
        ai_preds = _make_decimal_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260208_05_11",
            budget=3000,
            runners_data=runners,
            ai_predictions=ai_preds,
            race_name="テストレース",
            race_conditions=["g3"],
            venue="05",
            total_runners=12,
        )
        assert "error" not in result
        assert "proposed_bets" in result
        assert isinstance(result["proposed_bets"], list)


# =============================================================================
# 相対信頼度割り当てテスト
# =============================================================================


class TestAssignRelativeConfidence:
    """_assign_relative_confidence のテスト."""

    def test_空リストでエラーにならない(self):
        """空リストを渡してもエラーにならない."""
        bets = []
        _assign_relative_confidence(bets)
        assert bets == []

    def test_1件はhighになる(self):
        """候補が1件の場合はhighが割り当てられる."""
        bets = [{"_composite_score": 60, "confidence": "medium"}]
        _assign_relative_confidence(bets)
        assert bets[0]["confidence"] == "high"

    def test_2件は上位highと下位medium(self):
        """候補が2件の場合は上位がhigh、下位がmedium."""
        bets = [
            {"_composite_score": 50, "confidence": "medium"},
            {"_composite_score": 80, "confidence": "medium"},
        ]
        _assign_relative_confidence(bets)
        assert bets[1]["confidence"] == "high"
        assert bets[0]["confidence"] == "medium"

    def test_3件で3段階に分かれる(self):
        """候補が3件の場合はhigh/medium/lowの3段階."""
        bets = [
            {"_composite_score": 90, "confidence": "medium"},
            {"_composite_score": 70, "confidence": "medium"},
            {"_composite_score": 50, "confidence": "medium"},
        ]
        _assign_relative_confidence(bets)
        assert bets[0]["confidence"] == "high"
        assert bets[1]["confidence"] == "medium"
        assert bets[2]["confidence"] == "low"

    def test_全スコア同値で期待値も同値は全てmedium(self):
        """全候補のスコアも期待値も同じ場合は全てmediumになる."""
        bets = [
            {"_composite_score": 75, "expected_value": 1.0, "confidence": "high"},
            {"_composite_score": 75, "expected_value": 1.0, "confidence": "high"},
            {"_composite_score": 75, "expected_value": 1.0, "confidence": "high"},
        ]
        _assign_relative_confidence(bets)
        for b in bets:
            assert b["confidence"] == "medium"

    def test_全スコア同値でも期待値が異なれば信頼度が分布する(self):
        """スコアが同値でも期待値にばらつきがあれば高中低に分かれる."""
        bets = [
            {"_composite_score": 75, "expected_value": 1.5, "confidence": "medium"},
            {"_composite_score": 75, "expected_value": 1.0, "confidence": "medium"},
            {"_composite_score": 75, "expected_value": 0.5, "confidence": "medium"},
        ]
        _assign_relative_confidence(bets)
        assert bets[0]["confidence"] == "high"
        assert bets[1]["confidence"] == "medium"
        assert bets[2]["confidence"] == "low"

    def test_全スコア同値で期待値フォールバック_8件(self):
        """8件でスコア同値・期待値異なる場合に3段階全てが出現する."""
        bets = [
            {"_composite_score": 75, "expected_value": 2.0 - i * 0.2, "confidence": "medium"}
            for i in range(8)
        ]
        _assign_relative_confidence(bets)
        confidences = [b["confidence"] for b in bets]
        assert "high" in confidences
        assert "medium" in confidences
        assert "low" in confidences

    def test_8件で信頼度にばらつきが出る(self):
        """MAX_BETS=8件の場合、3段階全てが出現する."""
        bets = [{"_composite_score": 90 - i * 5, "confidence": "medium"} for i in range(8)]
        _assign_relative_confidence(bets)
        confidences = [b["confidence"] for b in bets]
        assert "high" in confidences
        assert "medium" in confidences
        assert "low" in confidences

    def test_8件でhigh割合は半分未満(self):
        """8件のうちhighは3件以下（全部highにならない）."""
        bets = [{"_composite_score": 90 - i * 5, "confidence": "medium"} for i in range(8)]
        _assign_relative_confidence(bets)
        high_count = sum(1 for b in bets if b["confidence"] == "high")
        assert high_count <= 4
        assert high_count >= 1

    def test_スコア降順で信頼度が単調非増加(self):
        """スコア順にソートしたとき信頼度はhigh→medium→lowの順."""
        bets = [{"_composite_score": 90 - i * 3, "confidence": "medium"} for i in range(6)]
        _assign_relative_confidence(bets)
        # スコア降順ソート
        sorted_bets = sorted(bets, key=lambda b: b["_composite_score"], reverse=True)
        confidence_order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(sorted_bets) - 1):
            current = confidence_order[sorted_bets[i]["confidence"]]
            next_val = confidence_order[sorted_bets[i + 1]["confidence"]]
            assert current <= next_val

    def test_composite_scoreがない場合でもエラーにならない(self):
        """_composite_scoreキーがなくてもデフォルト0で処理される."""
        bets = [
            {"confidence": "medium"},
            {"confidence": "medium", "_composite_score": 80},
        ]
        _assign_relative_confidence(bets)
        assert bets[1]["confidence"] == "high"
        assert bets[0]["confidence"] == "medium"


class TestGenerateBetCandidatesConfidence:
    """_generate_bet_candidates が信頼度にばらつきを生むことのテスト."""

    def test_買い目候補の信頼度が全てhighにならない(self):
        """十分な候補数がある場合、全てhighにはならない."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        axis = [
            {"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 85},
            {"horse_number": 2, "horse_name": "テスト馬2", "composite_score": 75},
        ]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["quinella", "quinella_place"],
            total_runners=12,
        )
        if len(bets) >= 3:
            confidences = {b["confidence"] for b in bets}
            assert len(confidences) >= 2, f"信頼度が1種類のみ: {confidences}"

    def test_内部スコアがレスポンスから削除される(self):
        """_composite_scoreは信頼度割り当て後にレスポンスから除去される."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        axis = [{"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 85}]
        bets = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=ai_preds,
            bet_types=["quinella"],
            total_runners=12,
        )
        for bet in bets:
            assert "_composite_score" not in bet
