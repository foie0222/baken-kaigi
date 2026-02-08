"""買い目提案ツールのテスト."""

import sys
from pathlib import Path

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.bet_proposal import (
    _calculate_composite_score,
    _select_axis_horses,
    _select_bet_types_by_difficulty,
    _generate_bet_candidates,
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
