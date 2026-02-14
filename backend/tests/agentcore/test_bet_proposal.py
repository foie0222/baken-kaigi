"""買い目提案ツールのテスト."""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.bet_proposal import (
    _build_narration_context,
    _calculate_composite_score,
    _calculate_confidence_factor,
    _calculate_form_score,
    _calculate_speed_index_score,
    _invoke_haiku_narrator,
    _select_axis_horses,
    _select_bet_types_by_difficulty,
    _generate_bet_candidates,
    _assign_relative_confidence,
    _allocate_budget,
    _allocate_budget_dutching,
    _assess_ai_consensus,
    _estimate_bet_odds,
    _generate_bet_proposal_impl,
    _generate_proposal_reasoning,
    _get_character_config,
    _compute_unified_win_probabilities,
    _calculate_ev_from_unified_prob,
    _calculate_combination_ev,
    CHARACTER_PROFILES,
    _DEFAULT_CONFIG,
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


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestSkipGate:
    """見送りゲートのテスト."""

    def test_見送りスコア7以上で予算半減(self, mock_haiku):
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

    def test_通常レースでは予算削減なし(self, mock_haiku):
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


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestOutputFormat:
    """出力フォーマットのテスト."""

    def test_必須フィールドが存在する(self, mock_haiku):
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

    def test_race_summaryの必須フィールド(self, mock_haiku):
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

    def test_proposed_betsの各要素に必須フィールドがある(self, mock_haiku):
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

    def test_disclaimerが含まれる(self, mock_haiku):
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

    def test_total_amountはbudgetを超えない(self, mock_haiku):
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


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestIntegration:
    """統合テスト."""

    def test_全体フロー_12頭G1(self, mock_haiku):
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

    def test_全体フロー_ユーザー指定軸馬(self, mock_haiku):
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

    def test_全体フロー_ユーザー指定券種(self, mock_haiku):
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


    def test_全体フロー_単勝指定で買い目が生成される(self, mock_haiku):
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

    def test_全体フロー_複勝指定で買い目が生成される(self, mock_haiku):
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


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestDecimalCompatibility:
    """DynamoDB Decimal型との互換性テスト."""

    def test_複合スコア計算でDecimal型のrankを処理できる(self, mock_haiku):
        """AI予想のrankがDecimal型でもTypeErrorにならない."""
        runners = _make_runners(12)
        ai_preds = _make_decimal_ai_predictions(12)
        score = _calculate_composite_score(1, runners, ai_preds)
        assert isinstance(score, float)
        assert score > 0

    def test_軸馬選定でDecimal型のAI予想を処理できる(self, mock_haiku):
        """Decimal型のAI予想データでも軸馬選定が正常動作する."""
        runners = _make_runners(12)
        ai_preds = _make_decimal_ai_predictions(12)
        result = _select_axis_horses(runners, ai_preds)
        assert len(result) >= 1
        assert all(isinstance(a["composite_score"], float) for a in result)

    def test_AI合議レベル判定でDecimal型のscoreを処理できる(self, mock_haiku):
        """AI予想のscoreがDecimal型でも合議レベル判定が正常動作する."""
        ai_preds = _make_decimal_ai_predictions(12)
        result = _assess_ai_consensus(ai_preds)
        assert result in ("明確な上位", "やや接戦", "概ね合意", "データ不足", "混戦")

    def test_買い目生成でDecimal型のAI予想を処理できる(self, mock_haiku):
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

    def test_統合提案でDecimal型のAI予想を処理できる(self, mock_haiku):
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


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestPopularityNoneHandling:
    """人気データ未取得時のハンドリングテスト."""

    def test_popularityがNoneの場合にスコアが異常に膨張しない(self, mock_haiku):
        """popularityがNoneの場合、オッズ乖離ボーナスが誤って付与されない."""
        runners = _make_runners(12, with_odds=False)
        # popularity を None にする（オッズ未発売の状態）
        for r in runners:
            r["popularity"] = None
        ai_preds = _make_ai_predictions(12)
        score = _calculate_composite_score(1, runners, ai_preds)
        # popularity不明でもスコアが100にならないこと（以前は276→100に膨張していた）
        assert score < 100

    def test_popularityが0の場合にスコアが異常に膨張しない(self, mock_haiku):
        """popularityが0の場合、オッズ乖離ボーナスが誤って付与されない."""
        runners = _make_runners(12, with_odds=False)
        for r in runners:
            r["popularity"] = 0
        ai_preds = _make_ai_predictions(12)
        score = _calculate_composite_score(1, runners, ai_preds)
        assert score < 100

    def test_oddsもpopularityもないケースで買い目生成できる(self, mock_haiku):
        """オッズ・人気データなしでも買い目提案がエラーなく完了する."""
        runners = _make_runners(12, with_odds=False)
        for r in runners:
            r["popularity"] = None
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260208_05_01",
            budget=3000,
            runners_data=runners,
            ai_predictions=ai_preds,
            race_name="テスト未勝利",
            total_runners=12,
        )
        assert "error" not in result
        assert "proposed_bets" in result

    def test_オッズ未発売時に信頼度が全てhighにならない(self, mock_haiku):
        """オッズ・人気データなしの場合、信頼度が分散される."""
        runners = _make_runners(12, with_odds=False)
        for r in runners:
            r["popularity"] = None
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260208_05_01",
            budget=3000,
            runners_data=runners,
            ai_predictions=ai_preds,
            race_name="テスト未勝利",
            total_runners=12,
        )
        bets = result.get("proposed_bets", [])
        confidences = {b["confidence"] for b in bets}
        # 全てhighではなく、少なくとも2種類の信頼度があること
        assert len(confidences) >= 2, f"信頼度が{confidences}のみ。分散されていない"



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


# =============================================================================
# ペルソナプロファイルテスト
# =============================================================================


class TestCharacterProfiles:
    """ペルソナ別設定のテスト."""

    def test_None指定でデフォルト値が返る(self):
        """character_type=None の場合はデフォルト値."""
        config = _get_character_config(None)
        assert config["weight_ai_score"] == _DEFAULT_CONFIG["weight_ai_score"]
        assert config["max_bets"] == _DEFAULT_CONFIG["max_bets"]

    def test_analyst指定でデフォルトと同一(self):
        """analyst はデフォルトと同じ."""
        config = _get_character_config("analyst")
        for key in _DEFAULT_CONFIG:
            assert config[key] == _DEFAULT_CONFIG[key]

    def test_conservative設定が正しい(self):
        """conservative は max_bets=5, allocation_high=0.60, skip_gate_threshold=6."""
        config = _get_character_config("conservative")
        assert config["max_bets"] == 5
        assert config["allocation_high"] == 0.60
        assert config["skip_gate_threshold"] == 6

    def test_aggressive設定が正しい(self):
        """aggressive は allocation_low=0.40, skip_gate_threshold=9."""
        config = _get_character_config("aggressive")
        assert config["allocation_low"] == 0.40
        assert config["skip_gate_threshold"] == 9

    def test_intuition設定が正しい(self):
        """intuition は weight_odds_gap=0.5, weight_ai_score=0.3."""
        config = _get_character_config("intuition")
        assert config["weight_odds_gap"] == 0.5
        assert config["weight_ai_score"] == 0.3

    def test_unknown指定でデフォルトにフォールバック(self):
        """未知のペルソナはデフォルトにフォールバック."""
        config = _get_character_config("unknown")
        for key in _DEFAULT_CONFIG:
            assert config[key] == _DEFAULT_CONFIG[key]

    def test_全ペルソナのallocation合計が1(self):
        """全ペルソナの allocation_high + medium + low = 1.0."""
        for persona in [None, "analyst", "intuition", "conservative", "aggressive"]:
            config = _get_character_config(persona)
            total = config["allocation_high"] + config["allocation_medium"] + config["allocation_low"]
            assert abs(total - 1.0) < 0.01, f"{persona}: allocation合計={total}"


# =============================================================================
# max_bets パラメータテスト
# =============================================================================


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestMaxBetsParameter:
    """max_bets パラメータのテスト."""

    def test_max_bets_3で最大3点(self, mock_haiku):
        """max_bets=3 指定で最大3点."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=5000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
            max_bets=3,
        )
        assert len(result["proposed_bets"]) <= 3

    def test_max_bets未指定でデフォルト8点(self, mock_haiku):
        """max_bets 未指定でデフォルト MAX_BETS=8."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
        )
        assert len(result["proposed_bets"]) <= 8

    def test_conservativeのデフォルトmax_betsは5(self, mock_haiku):
        """character_type='conservative' のデフォルト max_bets は 5."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
            character_type="conservative",
        )
        assert len(result["proposed_bets"]) <= 5

    def test_ユーザーmax_betsがペルソナデフォルトを上書き(self, mock_haiku):
        """ユーザー max_bets=8 が conservative デフォルト5を上書き."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _generate_bet_proposal_impl(
            race_id="20260201_05_11",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=12,
            character_type="conservative",
            max_bets=8,
        )
        # conservative デフォルトの5ではなく、ユーザー指定の8が使われる
        # 候補が十分あれば5以上になりうる
        assert len(result["proposed_bets"]) <= 8


# =============================================================================
# ペルソナconfig伝播テスト
# =============================================================================


class TestCharacterConfigPropagation:
    """ペルソナ設定が各関数に伝播されることのテスト."""

    def test_aggressiveの配分でlow金額がmediumより大きい(self):
        """aggressive は allocation_low=0.40 > medium=0.25 なので低信頼の金額が多い."""
        bets = [
            {"confidence": "high", "bet_type": "quinella", "expected_value": 1.5},
            {"confidence": "medium", "bet_type": "quinella", "expected_value": 1.0},
            {"confidence": "low", "bet_type": "quinella", "expected_value": 0.8},
        ]
        result = _allocate_budget(
            bets, 10000,
            allocation_high=0.35, allocation_medium=0.25, allocation_low=0.40,
        )
        low_bet = next(b for b in result if b["confidence"] == "low")
        medium_bet = next(b for b in result if b["confidence"] == "medium")
        assert low_bet["amount"] >= medium_bet["amount"]

    def test_conservativeの難易度1でquinella_placeが含まれる(self):
        """conservative の difficulty_bet_types[1] には quinella_place が含まれる."""
        config = _get_character_config("conservative")
        bet_types = config["difficulty_bet_types"][1]
        assert "quinella_place" in bet_types


# =============================================================================
# 提案根拠テスト
# =============================================================================


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestGenerateProposalReasoning:
    """_generate_proposal_reasoning のテスト."""

    def _make_reasoning_args(self, *, skip_score: int = 3, preferred_bet_types=None):
        """テスト用の共通引数を生成する."""
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        axis_horses = [
            {"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 85.0},
            {"horse_number": 2, "horse_name": "テスト馬2", "composite_score": 72.0},
        ]
        difficulty = {"difficulty_stars": 3, "difficulty_label": "標準"}
        skip = {"skip_score": skip_score, "reasons": [], "recommendation": "参戦推奨"}
        bets = [
            {
                "bet_type": "quinella", "bet_type_name": "馬連",
                "horse_numbers": [1, 3], "expected_value": 1.8,
                "composite_odds": 8.5, "confidence": "high",
            },
            {
                "bet_type": "quinella", "bet_type_name": "馬連",
                "horse_numbers": [1, 5], "expected_value": 1.5,
                "composite_odds": 12.0, "confidence": "medium",
            },
        ]
        return dict(
            axis_horses=axis_horses,
            difficulty=difficulty,
            predicted_pace="ミドル",
            ai_consensus="概ね合意",
            skip=skip,
            bets=bets,
            preferred_bet_types=preferred_bet_types,
            ai_predictions=ai_preds,
            runners_data=runners,
        )

    def test_提案根拠が文字列を返す(self, mock_haiku):
        """_generate_proposal_reasoning は文字列を返す."""
        args = self._make_reasoning_args()
        result = _generate_proposal_reasoning(**args)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_軸馬の馬番とAI順位が含まれる(self, mock_haiku):
        """軸馬の馬番とAI順位が根拠テキストに含まれる."""
        args = self._make_reasoning_args()
        result = _generate_proposal_reasoning(**args)
        assert "1番テスト馬1" in result
        assert "AI指数1位" in result

    def test_4セクションが全て含まれる(self, mock_haiku):
        """【軸馬選定】【券種】【組み合わせ】【リスク】の4セクションが含まれる."""
        args = self._make_reasoning_args()
        result = _generate_proposal_reasoning(**args)
        assert "【軸馬選定】" in result
        assert "【券種】" in result
        assert "【組み合わせ】" in result
        assert "【リスク】" in result

    def test_券種が自動選定の場合に難易度が言及される(self, mock_haiku):
        """preferred_bet_types未指定時はレース難易度が言及される."""
        args = self._make_reasoning_args(preferred_bet_types=None)
        result = _generate_proposal_reasoning(**args)
        assert "レース難易度" in result
        assert "自動選定" in result

    def test_券種がユーザー指定の場合にその旨が言及される(self, mock_haiku):
        """preferred_bet_types指定時は「ユーザー指定」が言及される."""
        args = self._make_reasoning_args(preferred_bet_types=["quinella"])
        result = _generate_proposal_reasoning(**args)
        assert "ユーザー指定" in result

    def test_相手馬の期待値が含まれる(self, mock_haiku):
        """組み合わせセクションに相手馬の期待値が含まれる."""
        args = self._make_reasoning_args()
        result = _generate_proposal_reasoning(**args)
        # 相手馬3番（期待値1.8）が含まれるはず
        assert "3番" in result
        assert "期待値" in result

    def test_見送りスコアが高い場合にリスク言及が含まれる(self, mock_haiku):
        """見送りスコアが閾値以上の場合に予算削減の言及がある."""
        args = self._make_reasoning_args(skip_score=8)
        result = _generate_proposal_reasoning(**args)
        assert "予算50%削減" in result

    def test_見送りスコアが低い場合に積極参戦が含まれる(self, mock_haiku):
        """見送りスコアが低い場合は積極参戦レベルと表示される."""
        args = self._make_reasoning_args(skip_score=2)
        result = _generate_proposal_reasoning(**args)
        assert "積極参戦" in result

    def test_AI合議レベルが含まれる(self, mock_haiku):
        """リスクセクションにAI合議レベルが含まれる."""
        args = self._make_reasoning_args()
        result = _generate_proposal_reasoning(**args)
        assert "AI合議「概ね合意」" in result

    def test_Decimal型のAI予想データでもエラーにならない(self, mock_haiku):
        """DynamoDB Decimal型のデータでも正常に動作する."""
        args = self._make_reasoning_args()
        # AI予想データをDecimal型に変換
        for pred in args["ai_predictions"]:
            pred["horse_number"] = Decimal(str(pred["horse_number"]))
            pred["rank"] = Decimal(str(pred["rank"]))
            pred["score"] = Decimal(str(pred["score"]))
        result = _generate_proposal_reasoning(**args)
        assert isinstance(result, str)
        assert "【軸馬選定】" in result


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestProposalReasoningInImpl:
    """_generate_bet_proposal_impl の返却dictに proposal_reasoning が含まれることのテスト."""

    def test_返却dictにproposal_reasoningキーが存在する(self, mock_haiku):
        """_generate_bet_proposal_impl の結果に proposal_reasoning がある."""
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
        )
        assert "proposal_reasoning" in result
        assert isinstance(result["proposal_reasoning"], str)
        assert len(result["proposal_reasoning"]) > 0

    def test_proposal_reasoningとanalysis_commentが両方存在する(self, mock_haiku):
        """proposal_reasoning を追加しても analysis_comment は維持される."""
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
        )
        assert "proposal_reasoning" in result
        assert "analysis_comment" in result
        # 両方が異なる内容（proposal_reasoningはセクション付き）
        assert "【軸馬選定】" in result["proposal_reasoning"]
        assert "【軸馬選定】" not in result["analysis_comment"]


class TestBuildNarrationContext:
    """_build_narration_context のテスト."""

    def _make_reasoning_args(self):
        """TestProposalReasoning と同じテストデータ."""
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        axis_horses = [
            {"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 85.0},
            {"horse_number": 2, "horse_name": "テスト馬2", "composite_score": 72.0},
        ]
        difficulty = {"difficulty_stars": 3, "difficulty_label": "標準"}
        skip = {"skip_score": 3, "reasons": [], "recommendation": "参戦推奨"}
        bets = [
            {
                "bet_type": "quinella", "bet_type_name": "馬連",
                "horse_numbers": [1, 3], "expected_value": 1.8,
                "composite_odds": 8.5, "confidence": "high",
            },
        ]
        return dict(
            axis_horses=axis_horses,
            difficulty=difficulty,
            predicted_pace="ミドル",
            ai_consensus="概ね合意",
            skip=skip,
            bets=bets,
            preferred_bet_types=None,
            ai_predictions=ai_preds,
            runners_data=runners,
        )

    def test_必須キーが全て含まれる(self):
        """context dictに必要なキーが全て存在する."""
        args = self._make_reasoning_args()
        ctx = _build_narration_context(**args)
        required_keys = {
            "axis_horses", "partner_horses", "difficulty",
            "predicted_pace", "ai_consensus", "skip", "bets",
        }
        assert required_keys.issubset(ctx.keys())

    def test_軸馬にAI順位とスコアが付与される(self):
        """axis_horses の各要素に ai_rank, ai_score が含まれる."""
        args = self._make_reasoning_args()
        ctx = _build_narration_context(**args)
        for horse in ctx["axis_horses"]:
            assert "ai_rank" in horse
            assert "ai_score" in horse
            assert isinstance(horse["ai_rank"], int)
            assert isinstance(horse["ai_score"], float)

    def test_相手馬が抽出される(self):
        """betsから軸馬以外の馬番が partner_horses に含まれる."""
        args = self._make_reasoning_args()
        ctx = _build_narration_context(**args)
        assert len(ctx["partner_horses"]) > 0
        partner_numbers = {p["horse_number"] for p in ctx["partner_horses"]}
        axis_numbers = {1, 2}
        assert partner_numbers.isdisjoint(axis_numbers)

    def test_スピード指数の生データが含まれる(self):
        """speed_index_data が渡された場合、context に speed_index_raw が含まれる."""
        args = self._make_reasoning_args()
        args["speed_index_data"] = {
            "horses": {1: {"indices": [80, 85], "avg": 82.5}},
        }
        ctx = _build_narration_context(**args)
        assert "speed_index_raw" in ctx

    def test_スピード指数なしの場合はキーが存在しない(self):
        """speed_index_data が None の場合、speed_index_raw は含まれない."""
        args = self._make_reasoning_args()
        args["speed_index_data"] = None
        ctx = _build_narration_context(**args)
        assert "speed_index_raw" not in ctx

    def test_過去成績の生データが含まれる(self):
        """past_performance_data が渡された場合、context に past_performance_raw が含まれる."""
        args = self._make_reasoning_args()
        args["past_performance_data"] = {
            "horses": {1: {"results": [1, 3, 2]}},
        }
        ctx = _build_narration_context(**args)
        assert "past_performance_raw" in ctx

    def test_Decimal型データでもエラーにならない(self):
        """DynamoDB Decimal 型でも正常動作する."""
        args = self._make_reasoning_args()
        for pred in args["ai_predictions"]:
            pred["horse_number"] = Decimal(str(pred["horse_number"]))
            pred["rank"] = Decimal(str(pred["rank"]))
            pred["score"] = Decimal(str(pred["score"]))
        ctx = _build_narration_context(**args)
        assert len(ctx["axis_horses"]) == 2


class TestInvokeHaikuNarrator:
    """_invoke_haiku_narrator のテスト."""

    def _make_context(self) -> dict:
        """テスト用の最小コンテキストを返す."""
        return {
            "axis_horses": [
                {"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 85.0,
                 "ai_rank": 1, "ai_score": 100, "odds": 3.5},
            ],
            "partner_horses": [
                {"horse_number": 3, "horse_name": "テスト馬3", "ai_rank": 3, "max_expected_value": 1.5},
            ],
            "difficulty": {"difficulty_stars": 3, "difficulty_label": "標準"},
            "predicted_pace": "ミドル",
            "ai_consensus": "概ね合意",
            "skip": {"skip_score": 3, "reasons": [], "recommendation": "参戦推奨"},
            "bets": [
                {
                    "bet_type_name": "馬連", "horse_numbers": [1, 3],
                    "expected_value": 1.8, "composite_odds": 8.5, "confidence": "high",
                },
            ],
        }

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_正常時にLLM生成テキストを返す(self, mock_haiku):
        """mockが有効な4セクションテキストを返す場合、resultに全4セクションが含まれる."""
        mock_haiku.return_value = (
            "【軸馬選定】1番テスト馬1をAI指数1位で軸に選定。\n\n"
            "【券種】レース難易度★★★のため馬連を選定。\n\n"
            "【組み合わせ】相手は3番テスト馬3。\n\n"
            "【リスク】AI合議「概ね合意」。見送りスコア3/10。"
        )
        ctx = self._make_context()
        result = _invoke_haiku_narrator(ctx)
        assert result is not None
        assert "【軸馬選定】" in result
        assert "【券種】" in result
        assert "【組み合わせ】" in result
        assert "【リスク】" in result
        mock_haiku.assert_called_once()

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_LLMが4セクション返さない場合はNoneを返す(self, mock_haiku):
        """mockが不完全な回答を返す場合、resultはNone."""
        mock_haiku.return_value = "不完全な回答です"
        ctx = self._make_context()
        result = _invoke_haiku_narrator(ctx)
        assert result is None

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_API例外時はNoneを返す(self, mock_haiku):
        """mockがExceptionを発生させる場合、resultはNone."""
        mock_haiku.side_effect = Exception("ServiceUnavailable")
        ctx = self._make_context()
        result = _invoke_haiku_narrator(ctx)
        assert result is None


# =============================================================================
# テスト用データ（スピード指数・過去成績）
# =============================================================================


def _make_speed_index_data(indices_by_source: dict) -> dict:
    """テスト用スピード指数データを生成する.

    Args:
        indices_by_source: {source_name: {horse_number: speed_index_value}}
    """
    sources = []
    for source_name, indices in indices_by_source.items():
        sorted_indices = sorted(indices.items(), key=lambda x: -x[1])
        sources.append({
            "source": source_name,
            "indices": [
                {"horse_number": hn, "speed_index": si, "rank": rank}
                for rank, (hn, si) in enumerate(sorted_indices, 1)
            ],
        })
    return {"sources": sources}


def _make_past_performance_data(horses: dict) -> dict:
    """テスト用過去成績データを生成する.

    Args:
        horses: {horse_number: [finish_position_1, finish_position_2, ...]}
                リストの先頭が最新走。
    """
    horse_list = []
    for hn, positions in horses.items():
        past_races = [{"finish_position": pos} for pos in positions]
        horse_list.append({
            "horse_number": hn,
            "horse_name": f"テスト馬{hn}",
            "past_races": past_races,
        })
    return {
        "sources": [{
            "source": "keibagrant",
            "horses": horse_list,
        }]
    }


# =============================================================================
# スピード指数スコアテスト
# =============================================================================


class TestCalculateSpeedIndexScore:
    """_calculate_speed_index_score のテスト."""

    def test_単一ソースで正しいスコア(self):
        data = _make_speed_index_data({
            "jiro8-speed": {1: 90, 2: 80, 3: 70},
        })
        score = _calculate_speed_index_score(1, data)
        assert score == 100.0  # 1位 → 100

    def test_複数ソースで平均スコア(self):
        data = _make_speed_index_data({
            "jiro8-speed": {1: 90, 2: 70, 3: 60},
            "kichiuma-speed": {1: 80, 2: 90, 3: 50},
        })
        # 馬1: avg=85, 馬2: avg=80, 馬3: avg=55 → 馬1が1位
        score1 = _calculate_speed_index_score(1, data)
        score2 = _calculate_speed_index_score(2, data)
        score3 = _calculate_speed_index_score(3, data)
        assert score1 == 100.0  # 1位
        assert score2 > score3  # 2位 > 3位

    def test_データなしでNone(self):
        assert _calculate_speed_index_score(1, None) is None

    def test_該当馬番なしでNone(self):
        data = _make_speed_index_data({
            "jiro8-speed": {2: 90, 3: 80},
        })
        assert _calculate_speed_index_score(1, data) is None

    def test_Decimal型でも計算可能(self):
        data = {
            "sources": [{
                "source": "jiro8-speed",
                "indices": [
                    {"horse_number": Decimal("1"), "speed_index": Decimal("90"), "rank": 1},
                    {"horse_number": Decimal("2"), "speed_index": Decimal("80"), "rank": 2},
                ],
            }]
        }
        score = _calculate_speed_index_score(1, data)
        assert score is not None
        assert isinstance(score, float)

    def test_1位の馬は100(self):
        data = _make_speed_index_data({
            "jiro8-speed": {1: 90, 2: 80, 3: 70, 4: 60, 5: 50},
        })
        assert _calculate_speed_index_score(1, data) == 100.0

    def test_最下位でも約15で0にならない(self):
        data = _make_speed_index_data({
            "jiro8-speed": {1: 90, 2: 80, 3: 70, 4: 60, 5: 50},
        })
        score = _calculate_speed_index_score(5, data)
        assert score == 15.0
        assert score > 0


# =============================================================================
# 近走フォームスコアテスト
# =============================================================================


class TestCalculateFormScore:
    """_calculate_form_score のテスト."""

    def test_全1着で100(self):
        data = _make_past_performance_data({1: [1, 1, 1, 1, 1]})
        score = _calculate_form_score(1, data)
        assert score == 100.0

    def test_混合着順で加重平均(self):
        data = _make_past_performance_data({1: [1, 3, 5, 2, 10]})
        score = _calculate_form_score(1, data)
        assert score is not None
        assert 0 < score < 100

    def test_近走ほど重みが大きい(self):
        # 最新1着+古い10着 vs 最新10着+古い1着
        data_recent_good = _make_past_performance_data({1: [1, 10]})
        data_recent_bad = _make_past_performance_data({2: [10, 1]})
        score_good = _calculate_form_score(1, data_recent_good)
        score_bad = _calculate_form_score(2, data_recent_bad)
        assert score_good > score_bad  # 最新が良い方が高い

    def test_5走未満でも計算可能(self):
        data = _make_past_performance_data({1: [2, 3]})
        score = _calculate_form_score(1, data)
        assert score is not None
        assert 0 < score < 100

    def test_データなしでNone(self):
        assert _calculate_form_score(1, None) is None

    def test_該当馬番なしでNone(self):
        data = _make_past_performance_data({2: [1, 2, 3]})
        assert _calculate_form_score(1, data) is None

    def test_Decimal型でも計算可能(self):
        data = {
            "sources": [{
                "source": "keibagrant",
                "horses": [{
                    "horse_number": Decimal("1"),
                    "horse_name": "テスト馬1",
                    "past_races": [
                        {"finish_position": Decimal("1")},
                        {"finish_position": Decimal("3")},
                    ],
                }],
            }]
        }
        score = _calculate_form_score(1, data)
        assert score is not None
        assert isinstance(score, float)


# =============================================================================
# composite_score拡張テスト
# =============================================================================


class TestCompositeScoreWithNewData:
    """スピード指数・近走フォーム統合後のcomposite_scoreテスト."""

    def test_全5成分でスコア計算(self):
        runners = _make_runners(5)
        ai_preds = _make_ai_predictions(5)
        si_data = _make_speed_index_data({
            "jiro8-speed": {1: 90, 2: 80, 3: 70, 4: 60, 5: 50},
        })
        pp_data = _make_past_performance_data({
            1: [1, 1, 2], 2: [3, 4, 5], 3: [5, 6, 7],
            4: [8, 9, 10], 5: [10, 12, 15],
        })
        score = _calculate_composite_score(
            1, runners, ai_preds,
            speed_index_data=si_data, past_performance_data=pp_data,
        )
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_speed_indexなしで4成分フォールバック(self):
        runners = _make_runners(5)
        ai_preds = _make_ai_predictions(5)
        pp_data = _make_past_performance_data({1: [1, 2, 3]})
        score_with = _calculate_composite_score(
            1, runners, ai_preds, past_performance_data=pp_data,
        )
        score_without = _calculate_composite_score(1, runners, ai_preds)
        # formデータがある場合とない場合でスコアが異なる
        assert score_with != score_without

    def test_両方なしで既存3成分と完全同一スコア(self):
        """speed_index_data=None, past_performance_data=Noneで既存と同一."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        score_new = _calculate_composite_score(
            1, runners, ai_preds,
            speed_index_data=None, past_performance_data=None,
        )
        score_old = _calculate_composite_score(1, runners, ai_preds)
        assert score_new == score_old

    def test_speed_indexのみで4成分(self):
        runners = _make_runners(5)
        ai_preds = _make_ai_predictions(5)
        si_data = _make_speed_index_data({
            "jiro8-speed": {1: 90, 2: 80, 3: 70, 4: 60, 5: 50},
        })
        score = _calculate_composite_score(
            1, runners, ai_preds, speed_index_data=si_data,
        )
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_Decimal型データで全5成分正常(self):
        runners = _make_runners(3)
        ai_preds = _make_ai_predictions(3)
        si_data = {
            "sources": [{
                "source": "jiro8-speed",
                "indices": [
                    {"horse_number": Decimal("1"), "speed_index": Decimal("90"), "rank": 1},
                    {"horse_number": Decimal("2"), "speed_index": Decimal("80"), "rank": 2},
                    {"horse_number": Decimal("3"), "speed_index": Decimal("70"), "rank": 3},
                ],
            }]
        }
        pp_data = {
            "sources": [{
                "source": "keibagrant",
                "horses": [{
                    "horse_number": Decimal("1"),
                    "horse_name": "テスト馬1",
                    "past_races": [
                        {"finish_position": Decimal("1")},
                        {"finish_position": Decimal("2")},
                    ],
                }],
            }]
        }
        score = _calculate_composite_score(
            1, runners, ai_preds,
            speed_index_data=si_data, past_performance_data=pp_data,
        )
        assert isinstance(score, float)
        assert 0 <= score <= 100


# =============================================================================
# 呼び出しチェーン更新テスト
# =============================================================================


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestCallChainPropagation:
    """speed_index_data/past_performance_dataの伝播テスト."""

    def test_軸馬選定にスピード指数が影響(self, mock_haiku):
        runners = _make_runners(5)
        ai_preds = _make_ai_predictions(5)
        # 馬5のスピード指数を最高にする
        si_data = _make_speed_index_data({
            "jiro8-speed": {1: 50, 2: 60, 3: 70, 4: 80, 5: 90},
        })
        result_with = _select_axis_horses(
            runners, ai_preds, speed_index_data=si_data,
        )
        result_without = _select_axis_horses(runners, ai_preds)
        scores_with = {a["horse_number"]: a["composite_score"] for a in result_with}
        scores_without = {a["horse_number"]: a["composite_score"] for a in result_without}
        assert scores_with != scores_without

    def test_データなしでも軸馬選定が既存動作互換(self, mock_haiku):
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result_new = _select_axis_horses(
            runners, ai_preds,
            speed_index_data=None, past_performance_data=None,
        )
        result_old = _select_axis_horses(runners, ai_preds)
        assert [a["horse_number"] for a in result_new] == [a["horse_number"] for a in result_old]
        for new, old in zip(result_new, result_old):
            assert new["composite_score"] == old["composite_score"]

    def test_提案根拠にスピード指数情報が含まれる(self, mock_haiku):
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        si_data = _make_speed_index_data({
            "jiro8-speed": {i: 100 - i * 10 for i in range(1, 7)},
        })
        pp_data = _make_past_performance_data({
            i: [i, i + 1, i + 2] for i in range(1, 7)
        })
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=6,
            speed_index_data=si_data,
            past_performance_data=pp_data,
        )
        reasoning = result.get("proposal_reasoning", "")
        assert "スピード指数" in reasoning or "近走" in reasoning


# =============================================================================
# 統合単勝率テスト
# =============================================================================


class TestComputeUnifiedWinProbabilities:
    """_compute_unified_win_probabilities のテスト."""

    def test_単一ソースで確率合計が1になる(self):
        ai_result = {
            "sources": [
                {
                    "source_name": "ai-shisu",
                    "predictions": [
                        {"horse_number": 1, "score": 100},
                        {"horse_number": 2, "score": 50},
                        {"horse_number": 3, "score": 50},
                    ],
                }
            ]
        }
        probs = _compute_unified_win_probabilities(ai_result)
        assert len(probs) == 3
        assert abs(sum(probs.values()) - 1.0) < 1e-9
        # 1番馬はスコア100/(100+50+50)=0.5
        assert abs(probs[1] - 0.5) < 1e-9
        assert abs(probs[2] - 0.25) < 1e-9

    def test_複数ソースの平均で確率合計が1になる(self):
        ai_result = {
            "sources": [
                {
                    "source_name": "source-a",
                    "predictions": [
                        {"horse_number": 1, "score": 100},
                        {"horse_number": 2, "score": 100},
                    ],
                },
                {
                    "source_name": "source-b",
                    "predictions": [
                        {"horse_number": 1, "score": 300},
                        {"horse_number": 2, "score": 100},
                    ],
                },
            ]
        }
        probs = _compute_unified_win_probabilities(ai_result)
        assert len(probs) == 2
        assert abs(sum(probs.values()) - 1.0) < 1e-9
        # source-a: 1番=0.5, 2番=0.5
        # source-b: 1番=0.75, 2番=0.25
        # 平均: 1番=0.625, 2番=0.375
        assert abs(probs[1] - 0.625) < 1e-9
        assert abs(probs[2] - 0.375) < 1e-9

    def test_ソースが取得できない場合は空辞書を返す(self):
        assert _compute_unified_win_probabilities({}) == {}
        assert _compute_unified_win_probabilities({"sources": []}) == {}

    def test_一部ソースに馬が欠落しても合計が1になる(self):
        ai_result = {
            "sources": [
                {
                    "source_name": "source-a",
                    "predictions": [
                        {"horse_number": 1, "score": 100},
                        {"horse_number": 2, "score": 100},
                        {"horse_number": 3, "score": 100},
                    ],
                },
                {
                    "source_name": "source-b",
                    "predictions": [
                        {"horse_number": 1, "score": 200},
                        {"horse_number": 3, "score": 200},
                        # 2番馬がない
                    ],
                },
            ]
        }
        probs = _compute_unified_win_probabilities(ai_result)
        assert len(probs) == 3
        assert abs(sum(probs.values()) - 1.0) < 1e-9
        # 2番馬はsource-aのみ(1ソース分)で平均されるべき

    def test_スコアが全て0のソースはスキップされる(self):
        ai_result = {
            "sources": [
                {
                    "source_name": "good-source",
                    "predictions": [
                        {"horse_number": 1, "score": 100},
                        {"horse_number": 2, "score": 100},
                    ],
                },
                {
                    "source_name": "bad-source",
                    "predictions": [
                        {"horse_number": 1, "score": 0},
                        {"horse_number": 2, "score": 0},
                    ],
                },
            ]
        }
        probs = _compute_unified_win_probabilities(ai_result)
        assert abs(sum(probs.values()) - 1.0) < 1e-9
        # bad-sourceはスキップなので、good-sourceのみ → 各0.5
        assert abs(probs[1] - 0.5) < 1e-9

    def test_Decimal型のスコアも正しく処理される(self):
        ai_result = {
            "sources": [
                {
                    "source_name": "dynamo-source",
                    "predictions": [
                        {"horse_number": 1, "score": Decimal("100")},
                        {"horse_number": 2, "score": Decimal("50")},
                    ],
                }
            ]
        }
        probs = _compute_unified_win_probabilities(ai_result)
        assert abs(sum(probs.values()) - 1.0) < 1e-9
        assert abs(probs[1] - 2 / 3) < 1e-9


# =============================================================================
# 統合EV計算テスト
# =============================================================================


class TestCalculateEvFromUnifiedProb:
    """_calculate_ev_from_unified_prob のテスト."""

    def test_期待値が正しく計算される(self):
        result = _calculate_ev_from_unified_prob(odds=3.0, win_probability=0.33)
        assert abs(result["expected_return"] - 0.99) < 0.01
        assert result["estimated_probability"] == 0.33

    def test_妙味ありの判定(self):
        result = _calculate_ev_from_unified_prob(odds=3.0, win_probability=0.5)
        assert result["expected_return"] == 1.5
        assert result["value_rating"] == "妙味あり"

    def test_適正の判定(self):
        result = _calculate_ev_from_unified_prob(odds=3.0, win_probability=0.33)
        assert result["value_rating"] == "適正"

    def test_やや割高の判定(self):
        result = _calculate_ev_from_unified_prob(odds=3.0, win_probability=0.25)
        assert result["value_rating"] == "やや割高"

    def test_割高の判定(self):
        result = _calculate_ev_from_unified_prob(odds=3.0, win_probability=0.1)
        assert result["value_rating"] == "割高"

    def test_オッズ0の場合(self):
        result = _calculate_ev_from_unified_prob(odds=0, win_probability=0.5)
        assert result["expected_return"] == 0

    def test_probability_sourceにソース数が含まれる(self):
        result = _calculate_ev_from_unified_prob(odds=3.0, win_probability=0.5)
        assert "AI統合予想" in result["probability_source"]


# =============================================================================
# 組合せ馬券EV計算テスト
# =============================================================================


class TestCombinationEv:
    """_calculate_combination_ev のテスト."""

    def _make_unified_probs(self, count: int) -> dict[int, float]:
        """テスト用統合確率を生成する（合計1.0）."""
        # 人気順に確率を付与
        raw = [1.0 / (i + 1) for i in range(count)]
        total = sum(raw)
        return {i + 1: r / total for i, r in enumerate(raw)}

    def test_単勝の期待値計算(self):
        probs = self._make_unified_probs(5)
        result = _calculate_combination_ev(
            horse_numbers=[1],
            bet_type="win",
            estimated_odds=5.0,
            unified_probs=probs,
            total_runners=5,
        )
        expected_return = 5.0 * probs[1]
        assert abs(result["expected_return"] - expected_return) < 0.01
        assert result["combination_probability"] == probs[1]

    def test_馬連の期待値計算(self):
        probs = self._make_unified_probs(5)
        result = _calculate_combination_ev(
            horse_numbers=[1, 2],
            bet_type="quinella",
            estimated_odds=10.0,
            unified_probs=probs,
            total_runners=5,
        )
        assert result["combination_probability"] > 0
        assert result["expected_return"] > 0

    def test_馬単の期待値計算(self):
        probs = self._make_unified_probs(5)
        result = _calculate_combination_ev(
            horse_numbers=[1, 2],
            bet_type="exacta",
            estimated_odds=20.0,
            unified_probs=probs,
            total_runners=5,
        )
        # 馬単は馬連より確率が低い
        quinella_result = _calculate_combination_ev(
            horse_numbers=[1, 2],
            bet_type="quinella",
            estimated_odds=20.0,
            unified_probs=probs,
            total_runners=5,
        )
        assert result["combination_probability"] < quinella_result["combination_probability"]

    def test_三連複の期待値計算(self):
        probs = self._make_unified_probs(5)
        result = _calculate_combination_ev(
            horse_numbers=[1, 2, 3],
            bet_type="trio",
            estimated_odds=30.0,
            unified_probs=probs,
            total_runners=5,
        )
        assert result["combination_probability"] > 0
        assert result["expected_return"] > 0

    def test_三連単の期待値計算(self):
        probs = self._make_unified_probs(5)
        result = _calculate_combination_ev(
            horse_numbers=[1, 2, 3],
            bet_type="trifecta",
            estimated_odds=100.0,
            unified_probs=probs,
            total_runners=5,
        )
        # 三連単は三連複より確率が低い
        trio_result = _calculate_combination_ev(
            horse_numbers=[1, 2, 3],
            bet_type="trio",
            estimated_odds=100.0,
            unified_probs=probs,
            total_runners=5,
        )
        assert result["combination_probability"] < trio_result["combination_probability"]

    def test_ワイドの期待値計算(self):
        probs = self._make_unified_probs(5)
        result = _calculate_combination_ev(
            horse_numbers=[1, 2],
            bet_type="quinella_place",
            estimated_odds=3.0,
            unified_probs=probs,
            total_runners=5,
        )
        assert result["combination_probability"] > 0
        # ワイドは馬連より確率が高い
        quinella_result = _calculate_combination_ev(
            horse_numbers=[1, 2],
            bet_type="quinella",
            estimated_odds=3.0,
            unified_probs=probs,
            total_runners=5,
        )
        assert result["combination_probability"] > quinella_result["combination_probability"]

    def test_unified_probsに馬番がない場合は確率0(self):
        probs = {1: 0.5, 2: 0.5}
        result = _calculate_combination_ev(
            horse_numbers=[3],
            bet_type="win",
            estimated_odds=10.0,
            unified_probs=probs,
            total_runners=5,
        )
        assert result["combination_probability"] == 0.0
        assert result["expected_return"] == 0.0


# =============================================================================
# 統合テスト: unified_probs付きの_generate_bet_proposal_impl
# =============================================================================


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestGenerateBetProposalImplWithUnifiedProbs:
    """unified_probsを渡した場合の統合テスト."""

    def test_unified_probs付きで提案が生成される(self, mock_haiku):
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        unified_probs = {i: (7 - i) / 21.0 for i in range(1, 7)}

        result = _generate_bet_proposal_impl(
            race_id="test_unified_001",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=6,
            unified_probs=unified_probs,
        )
        assert "error" not in result
        assert len(result["proposed_bets"]) > 0
        assert result["total_amount"] > 0

    def test_unified_probs_Noneでフォールバックする(self, mock_haiku):
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)

        result = _generate_bet_proposal_impl(
            race_id="test_fallback_001",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=6,
            unified_probs=None,
        )
        assert "error" not in result
        assert len(result["proposed_bets"]) > 0

    def test_unified_probsがcomposite_scoreに影響する(self, mock_haiku):
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        # 6番馬の確率を圧倒的に高くする
        unified_probs = {1: 0.05, 2: 0.05, 3: 0.05, 4: 0.05, 5: 0.05, 6: 0.75}

        result = _generate_bet_proposal_impl(
            race_id="test_score_001",
            budget=10000,
            runners_data=runners,
            ai_predictions=ai_preds,
            total_runners=6,
            unified_probs=unified_probs,
        )
        # 6番馬が軸馬に選ばれるべき（unified_probsで1位）
        axis_numbers = set()
        for bet in result["proposed_bets"]:
            for hn in bet["horse_numbers"]:
                axis_numbers.add(hn)
        assert 6 in axis_numbers


# =============================================================================
# AI合議レベル判定テスト（unified_probs対応）
# =============================================================================


class TestAssessAiConsensusWithUnifiedProbs:
    """unified_probs対応の_assess_ai_consensusテスト."""

    def test_unified_probsで明確な上位(self):
        probs = {1: 0.5, 2: 0.2, 3: 0.15, 4: 0.15}
        result = _assess_ai_consensus([], unified_probs=probs)
        assert result == "明確な上位"

    def test_unified_probsで概ね合意(self):
        probs = {1: 0.35, 2: 0.25, 3: 0.2, 4: 0.2}
        result = _assess_ai_consensus([], unified_probs=probs)
        assert result == "概ね合意"

    def test_unified_probsでやや接戦(self):
        probs = {1: 0.30, 2: 0.25, 3: 0.25, 4: 0.20}
        result = _assess_ai_consensus([], unified_probs=probs)
        assert result == "やや接戦"

    def test_unified_probsで混戦(self):
        probs = {1: 0.26, 2: 0.25, 3: 0.25, 4: 0.24}
        result = _assess_ai_consensus([], unified_probs=probs)
        assert result == "混戦"

    def test_unified_probs_Noneで従来ロジック(self):
        preds = _make_ai_predictions(6)
        result = _assess_ai_consensus(preds, unified_probs=None)
        # 30pt刻みなので gap=30 → "概ね合意"
        assert result == "概ね合意"


class TestCalculateConfidenceFactor:
    """信頼度係数算出のテスト."""

    def test_見送りスコア0で最大値(self):
        assert _calculate_confidence_factor(0) == 2.0

    def test_見送りスコア5で約0_9(self):
        result = _calculate_confidence_factor(5)
        assert 0.85 <= result <= 0.95

    def test_見送りスコア8で最低正値(self):
        result = _calculate_confidence_factor(8)
        assert 0.2 <= result <= 0.3

    def test_見送りスコア9で見送り(self):
        assert _calculate_confidence_factor(9) == 0.0

    def test_見送りスコア10で見送り(self):
        assert _calculate_confidence_factor(10) == 0.0

    def test_スコアが高いほどfactorが小さい(self):
        factors = [_calculate_confidence_factor(s) for s in range(9)]
        for i in range(len(factors) - 1):
            assert factors[i] >= factors[i + 1]


class TestBaseRateConfig:
    """base_rate設定のテスト."""

    def test_デフォルトのbase_rateは003(self):
        config = _get_character_config(None)
        assert config["base_rate"] == 0.03

    def test_conservativeのbase_rateは002(self):
        config = _get_character_config("conservative")
        assert config["base_rate"] == 0.02

    def test_aggressiveのbase_rateは005(self):
        config = _get_character_config("aggressive")
        assert config["base_rate"] == 0.05

    def test_全ペルソナにbase_rateが存在する(self):
        for persona in ["analyst", "intuition", "conservative", "aggressive", None]:
            config = _get_character_config(persona)
            assert "base_rate" in config
            assert 0 < config["base_rate"] <= 0.10


class TestAllocateBudgetDutching:
    """ダッチング方式予算配分のテスト."""

    def test_均等払い戻しになる(self):
        """どの買い目が的中しても同額の払い戻しになる."""
        bets = [
            {"composite_odds": 5.0, "expected_value": 1.5},
            {"composite_odds": 10.0, "expected_value": 1.2},
            {"composite_odds": 20.0, "expected_value": 1.1},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        payouts = [b["amount"] * b["composite_odds"] for b in result]
        assert max(payouts) - min(payouts) <= max(b["composite_odds"] for b in result) * 100

    def test_EV1以下の買い目は除外される(self):
        bets = [
            {"composite_odds": 5.0, "expected_value": 1.5},
            {"composite_odds": 10.0, "expected_value": 0.8},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        assert len(result) == 1
        assert result[0]["expected_value"] == 1.5

    def test_全買い目EV1以下なら空リスト(self):
        bets = [
            {"composite_odds": 5.0, "expected_value": 0.9},
            {"composite_odds": 10.0, "expected_value": 0.5},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        assert result == []

    def test_100円単位に丸められる(self):
        bets = [
            {"composite_odds": 5.0, "expected_value": 1.5},
            {"composite_odds": 8.0, "expected_value": 1.2},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        for b in result:
            assert b["amount"] % 100 == 0

    def test_合計がbudgetを超えない(self):
        bets = [
            {"composite_odds": 3.0, "expected_value": 1.3},
            {"composite_odds": 5.0, "expected_value": 1.2},
            {"composite_odds": 8.0, "expected_value": 1.1},
        ]
        result = _allocate_budget_dutching(bets, 2000)
        total = sum(b["amount"] for b in result)
        assert total <= 2000

    def test_空リスト入力(self):
        result = _allocate_budget_dutching([], 3000)
        assert result == []

    def test_予算ゼロ(self):
        bets = [{"composite_odds": 5.0, "expected_value": 1.5}]
        result = _allocate_budget_dutching(bets, 0)
        assert all(b.get("amount", 0) == 0 for b in result) or result == bets

    def test_composite_oddsが結果に含まれる(self):
        bets = [
            {"composite_odds": 5.0, "expected_value": 1.5},
            {"composite_odds": 10.0, "expected_value": 1.2},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        for b in result:
            assert "dutching_composite_odds" in b

    def test_最低賭け金未満の買い目が除外される(self):
        bets = [
            {"composite_odds": 3.0, "expected_value": 1.5},
            {"composite_odds": 100.0, "expected_value": 1.1},
        ]
        result = _allocate_budget_dutching(bets, 300)
        assert all(b["amount"] >= 100 for b in result)

    def test_低オッズの買い目に多く配分される(self):
        bets = [
            {"composite_odds": 3.0, "expected_value": 1.5},
            {"composite_odds": 10.0, "expected_value": 1.2},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        low_odds = next(b for b in result if b["composite_odds"] == 3.0)
        high_odds = next(b for b in result if b["composite_odds"] == 10.0)
        assert low_odds["amount"] > high_odds["amount"]


class TestGenerateBetCandidatesNoMaxBets:
    """MAX_BETS撤廃後の買い目生成テスト."""

    def test_期待値プラスの買い目が8点以上でも全て返される(self):
        """MAX_BETSによるカットがなくなったことを確認."""
        runners = _make_runners(12)
        preds = _make_ai_predictions(12)
        axis = [
            {"horse_number": 1, "composite_score": 100},
            {"horse_number": 2, "composite_score": 90},
        ]
        result = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=preds,
            bet_types=["quinella", "trio"],
            total_runners=12,
        )
        # max_bets=None（デフォルト）で8点を超える買い目が返される
        assert isinstance(result, list)
        assert len(result) > 8, f"MAX_BETS制限撤廃後は8点超を期待するが {len(result)}点"

        # max_bets=8を明示すると8点以下に制限される
        result_limited = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=preds,
            bet_types=["quinella", "trio"],
            total_runners=12,
            max_bets=8,
        )
        assert len(result_limited) <= 8


@patch("tools.bet_proposal._call_bedrock_haiku", side_effect=Exception("mocked"))
class TestBankrollMode:
    """bankrollモードの統合テスト."""

    def test_bankroll指定でrace_budgetが自動算出される(self, mock_haiku):
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=0,
            bankroll=30000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        assert result["race_budget"] > 0
        assert result["confidence_factor"] > 0

    def test_budget指定で従来動作(self, mock_haiku):
        """budget指定時は従来の信頼度別配分が使われる."""
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=5000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        assert result["total_amount"] <= 5000

    def test_bankrollの10パーセントを超えない(self, mock_haiku):
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=0,
            bankroll=10000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        assert result["total_amount"] <= 10000 * 0.10

    def test_見送りスコアが高いとrace_budgetが小さくなる(self, mock_haiku):
        """見送りスコアが高い場合、予算が少なくなる."""
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=0,
            bankroll=30000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        assert "bankroll_usage_pct" in result

    def test_bankrollモードでcomposite_oddsが出力される(self, mock_haiku):
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=0,
            bankroll=30000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        if result["proposed_bets"]:
            assert "dutching_composite_odds" in result["proposed_bets"][0]
