"""リスク分析ツールのテスト."""

import sys
from pathlib import Path

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.risk_analysis import (
    _assess_skip_recommendation,
    _analyze_excluded_horses,
    _generate_risk_scenarios,
    _diagnose_betting_bias,
    _analyze_near_miss,
    _analyze_risk_factors_impl,
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
            # 人気順にオッズを設定（1番人気=2.5倍、以降上昇）
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


# =============================================================================
# Phase 1: 見送り推奨テスト
# =============================================================================


class TestAssessSkipRecommendation:
    """見送り推奨のテスト."""

    def test_大荒れ条件は見送り推奨(self):
        """ハンデ戦 + 多頭数 + 荒れやすい競馬場 + AI混戦 → 見送り推奨."""
        runners = _make_runners(18)
        # AI上位5頭が混戦（スコア差小）
        ai_preds = [
            {"horse_number": i, "horse_name": f"テスト馬{i}", "rank": i, "score": 300 - (i - 1) * 5}
            for i in range(1, 19)
        ]
        result = _assess_skip_recommendation(
            total_runners=18,
            race_conditions=["handicap"],
            venue="福島",
            runners_data=runners,
            ai_predictions=ai_preds,
        )
        assert result["skip_score"] >= 7
        assert result["recommendation"] == "見送り推奨"

    def test_G1少頭数は見送り非推奨(self):
        """G1 + 少頭数 → 見送りを推奨しない."""
        runners = _make_runners(8)
        ai_preds = _make_ai_predictions(8)
        result = _assess_skip_recommendation(
            total_runners=8,
            race_conditions=["g1"],
            venue="東京",
            runners_data=runners,
            ai_predictions=ai_preds,
        )
        assert result["skip_score"] < 7
        assert result["recommendation"] != "見送り推奨"

    def test_AI混戦時はスコア上昇(self):
        """AI予想上位が僅差 → 予測困難でスコア上昇."""
        runners = _make_runners(16)
        # AI上位5頭のスコア差が小さい（混戦）
        ai_preds = [
            {"horse_number": i, "horse_name": f"テスト馬{i}", "rank": i, "score": 300 - (i - 1) * 5}
            for i in range(1, 17)
        ]
        result = _assess_skip_recommendation(
            total_runners=16,
            race_conditions=[],
            venue="東京",
            runners_data=runners,
            ai_predictions=ai_preds,
        )
        # 混戦なので通常よりスコアが上がる
        assert result["skip_score"] >= 4

    def test_ハンデ多頭数は高スコア(self):
        """ハンデ戦 + 多頭数 → スコアが高い."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        result = _assess_skip_recommendation(
            total_runners=18,
            race_conditions=["handicap"],
            venue="東京",
            runners_data=runners,
            ai_predictions=ai_preds,
        )
        assert result["skip_score"] >= 5

    def test_スコアは0から10の範囲(self):
        """スコアは0-10に収まる."""
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        result = _assess_skip_recommendation(
            total_runners=12,
            race_conditions=[],
            venue="東京",
            runners_data=runners,
            ai_predictions=ai_preds,
        )
        assert 0 <= result["skip_score"] <= 10

    def test_理由リストが返される(self):
        """判定理由がリストで返される."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        result = _assess_skip_recommendation(
            total_runners=18,
            race_conditions=["handicap"],
            venue="福島",
            runners_data=runners,
            ai_predictions=ai_preds,
        )
        assert isinstance(result["reasons"], list)
        assert len(result["reasons"]) > 0


# =============================================================================
# Phase 2: 除外馬分析テスト
# =============================================================================


class TestAnalyzeExcludedHorses:
    """除外馬リスク分析のテスト."""

    def test_上位人気を除外すると検出される(self):
        """1-3番人気を選択せず除外すると検出される."""
        runners = _make_runners(16)
        ai_preds = _make_ai_predictions(16)
        # 5,6,7番を選択（上位人気を除外）
        result = _analyze_excluded_horses(
            runners_data=runners,
            horse_numbers=[5, 6, 7],
            ai_predictions=ai_preds,
            total_runners=16,
        )
        # 除外馬に1-3番人気が含まれる
        excluded_numbers = [h["horse_number"] for h in result["excluded_horses"]]
        assert 1 in excluded_numbers
        assert 2 in excluded_numbers
        assert 3 in excluded_numbers

    def test_AI上位を除外すると検出される(self):
        """AI1位の馬を選択しない場合に検出される."""
        runners = _make_runners(16)
        ai_preds = _make_ai_predictions(16)
        # AI1位（馬番1）を除外して2,3,4を選択
        result = _analyze_excluded_horses(
            runners_data=runners,
            horse_numbers=[2, 3, 4],
            ai_predictions=ai_preds,
            total_runners=16,
        )
        excluded_numbers = [h["horse_number"] for h in result["excluded_horses"]]
        assert 1 in excluded_numbers

    def test_全馬選択時は除外馬なし(self):
        """全馬を選択した場合は除外馬リストが空."""
        runners = _make_runners(8)
        ai_preds = _make_ai_predictions(8)
        all_numbers = list(range(1, 9))
        result = _analyze_excluded_horses(
            runners_data=runners,
            horse_numbers=all_numbers,
            ai_predictions=ai_preds,
            total_runners=8,
        )
        assert len(result["excluded_horses"]) == 0

    def test_勝率が計算される(self):
        """除外馬に推定勝率が含まれる."""
        runners = _make_runners(16)
        ai_preds = _make_ai_predictions(16)
        result = _analyze_excluded_horses(
            runners_data=runners,
            horse_numbers=[5, 6, 7],
            ai_predictions=ai_preds,
            total_runners=16,
        )
        for horse in result["excluded_horses"]:
            assert "win_probability" in horse
            assert horse["win_probability"] > 0

    def test_危険度でソートされる(self):
        """除外馬は危険度順にソートされる."""
        runners = _make_runners(16)
        ai_preds = _make_ai_predictions(16)
        result = _analyze_excluded_horses(
            runners_data=runners,
            horse_numbers=[10, 11, 12],
            ai_predictions=ai_preds,
            total_runners=16,
        )
        # 最初の馬が最も危険度が高い（勝率が高い）
        if len(result["excluded_horses"]) >= 2:
            first_prob = result["excluded_horses"][0]["win_probability"]
            second_prob = result["excluded_horses"][1]["win_probability"]
            assert first_prob >= second_prob

    def test_上位5頭まで表示(self):
        """除外馬は最大5頭まで表示."""
        runners = _make_runners(18)
        ai_preds = _make_ai_predictions(18)
        # 1頭だけ選択（17頭除外）
        result = _analyze_excluded_horses(
            runners_data=runners,
            horse_numbers=[18],
            ai_predictions=ai_preds,
            total_runners=18,
        )
        assert len(result["excluded_horses"]) <= 5


# =============================================================================
# Phase 3: リスクシナリオテスト
# =============================================================================


class TestGenerateRiskScenarios:
    """リスクシナリオ生成のテスト."""

    def test_穴馬番狂わせシナリオ(self):
        """AI上位馬が未選択 → 穴馬番狂わせシナリオ."""
        runners = _make_runners(16)
        ai_preds = _make_ai_predictions(16)
        # AI上位を全て除外して下位を選択
        result = _generate_risk_scenarios(
            runners_data=runners,
            horse_numbers=[10, 11, 12],
            ai_predictions=ai_preds,
            race_conditions=[],
        )
        scenario_types = [s["type"] for s in result["scenarios"]]
        assert "穴馬番狂わせ" in scenario_types

    def test_本命飛びシナリオ(self):
        """1番人気を含む買い目 → 本命飛びシナリオ."""
        runners = _make_runners(16)
        result = _generate_risk_scenarios(
            runners_data=runners,
            horse_numbers=[1, 2, 3],
            ai_predictions=_make_ai_predictions(16),
            race_conditions=[],
        )
        scenario_types = [s["type"] for s in result["scenarios"]]
        assert "本命飛び" in scenario_types

    def test_シナリオは2から3件(self):
        """シナリオは2-3件に制限."""
        runners = _make_runners(18)
        result = _generate_risk_scenarios(
            runners_data=runners,
            horse_numbers=[1, 2, 3],
            ai_predictions=_make_ai_predictions(18),
            race_conditions=["handicap"],
        )
        assert 2 <= len(result["scenarios"]) <= 3

    def test_空データでもエラーにならない(self):
        """空データでも正常に動作する."""
        result = _generate_risk_scenarios(
            runners_data=[],
            horse_numbers=[],
            ai_predictions=[],
            race_conditions=[],
        )
        assert "scenarios" in result
        assert isinstance(result["scenarios"], list)

    def test_荒れレースシナリオ(self):
        """ハンデ戦/新馬戦 → 荒れレースシナリオ."""
        runners = _make_runners(16)
        result = _generate_risk_scenarios(
            runners_data=runners,
            horse_numbers=[1, 2, 3],
            ai_predictions=_make_ai_predictions(16),
            race_conditions=["handicap"],
        )
        scenario_types = [s["type"] for s in result["scenarios"]]
        assert "荒れレース" in scenario_types


# =============================================================================
# Phase 4: バイアス診断テスト
# =============================================================================


class TestDiagnoseBettingBias:
    """バイアス診断のテスト."""

    def test_穴馬偏重バイアス(self):
        """10番人気以下が多い → 穴馬偏重."""
        cart_items = [
            {"raceId": "R1", "betType": "win", "horseNumbers": [12], "amount": 100,
             "runners_data": _make_runners(16)},
            {"raceId": "R1", "betType": "win", "horseNumbers": [14], "amount": 100,
             "runners_data": _make_runners(16)},
            {"raceId": "R1", "betType": "win", "horseNumbers": [15], "amount": 100,
             "runners_data": _make_runners(16)},
        ]
        result = _diagnose_betting_bias(cart_items)
        bias_types = [b["type"] for b in result["biases"]]
        assert "穴馬偏重" in bias_types

    def test_本命偏重バイアス(self):
        """1-3番人気のみ → 本命偏重."""
        cart_items = [
            {"raceId": "R1", "betType": "trio", "horseNumbers": [1, 2, 3], "amount": 1000,
             "runners_data": _make_runners(16)},
            {"raceId": "R2", "betType": "quinella", "horseNumbers": [1, 2], "amount": 500,
             "runners_data": _make_runners(14)},
        ]
        result = _diagnose_betting_bias(cart_items)
        bias_types = [b["type"] for b in result["biases"]]
        assert "本命偏重" in bias_types

    def test_高配当券種偏重バイアス(self):
        """三連単/三連複のみ → 高配当券種偏重."""
        cart_items = [
            {"raceId": "R1", "betType": "trifecta", "horseNumbers": [1, 3, 5], "amount": 100,
             "runners_data": _make_runners(16)},
            {"raceId": "R2", "betType": "trio", "horseNumbers": [2, 4, 6], "amount": 100,
             "runners_data": _make_runners(14)},
            {"raceId": "R3", "betType": "trifecta", "horseNumbers": [1, 2, 3], "amount": 100,
             "runners_data": _make_runners(16)},
        ]
        result = _diagnose_betting_bias(cart_items)
        bias_types = [b["type"] for b in result["biases"]]
        assert "高配当券種偏重" in bias_types

    def test_過大投資バイアス(self):
        """合計金額が高い → 過大投資."""
        cart_items = [
            {"raceId": "R1", "betType": "win", "horseNumbers": [1], "amount": 10000,
             "runners_data": _make_runners(16)},
            {"raceId": "R2", "betType": "win", "horseNumbers": [2], "amount": 15000,
             "runners_data": _make_runners(14)},
        ]
        result = _diagnose_betting_bias(cart_items)
        bias_types = [b["type"] for b in result["biases"]]
        assert "過大投資" in bias_types

    def test_バイアスなし(self):
        """バランスの良い買い目 → バイアスなし."""
        cart_items = [
            {"raceId": "R1", "betType": "win", "horseNumbers": [3], "amount": 500,
             "runners_data": _make_runners(16)},
            {"raceId": "R1", "betType": "quinella", "horseNumbers": [3, 7], "amount": 300,
             "runners_data": _make_runners(16)},
        ]
        result = _diagnose_betting_bias(cart_items)
        assert len(result["biases"]) == 0

    def test_カート空(self):
        """カートが空の場合."""
        result = _diagnose_betting_bias([])
        assert len(result["biases"]) == 0

    def test_複合バイアス検出(self):
        """穴馬偏重 + 高配当券種偏重 が同時に検出される."""
        cart_items = [
            {"raceId": "R1", "betType": "trifecta", "horseNumbers": [10, 12, 14], "amount": 100,
             "runners_data": _make_runners(16)},
            {"raceId": "R2", "betType": "trio", "horseNumbers": [11, 13, 15], "amount": 100,
             "runners_data": _make_runners(16)},
            {"raceId": "R3", "betType": "trifecta", "horseNumbers": [12, 14, 16], "amount": 100,
             "runners_data": _make_runners(16)},
        ]
        result = _diagnose_betting_bias(cart_items)
        bias_types = [b["type"] for b in result["biases"]]
        assert "穴馬偏重" in bias_types
        assert "高配当券種偏重" in bias_types


# =============================================================================
# Phase 5: ニアミス分析テスト
# =============================================================================


class TestAnalyzeNearMiss:
    """ニアミス分析（スタブ）のテスト."""

    def test_スタブメッセージが返される(self):
        """スタブはレース結果確定後に利用可能というメッセージを返す."""
        result = _analyze_near_miss(
            race_id="202602010511",
            horse_numbers=[1, 2, 3],
            bet_type="trio",
        )
        assert result["status"] == "unavailable"
        assert "レース結果確定後" in result["message"]


# =============================================================================
# Phase 6: 統合テスト
# =============================================================================


class TestAnalyzeRiskFactorsImpl:
    """リスク分析統合のテスト."""

    def test_全項目が返却される(self):
        """全5項目の分析結果が含まれる."""
        runners = _make_runners(16)
        ai_preds = _make_ai_predictions(16)
        result = _analyze_risk_factors_impl(
            race_id="202602010511",
            horse_numbers=[1, 2, 3],
            runners_data=runners,
            ai_predictions=ai_preds,
            race_conditions=[],
            venue="東京",
            total_runners=16,
            cart_items=[
                {"raceId": "202602010511", "betType": "trio",
                 "horseNumbers": [1, 2, 3], "amount": 500,
                 "runners_data": runners},
            ],
        )
        assert "risk_scenarios" in result
        assert "excluded_horses" in result
        assert "skip_recommendation" in result
        assert "betting_bias" in result
        assert "near_miss" in result

    def test_カートなしでもバイアス分析はnullにならない(self):
        """カートが空でもbetting_biasは空リストで返される."""
        runners = _make_runners(16)
        ai_preds = _make_ai_predictions(16)
        result = _analyze_risk_factors_impl(
            race_id="202602010511",
            horse_numbers=[1, 2, 3],
            runners_data=runners,
            ai_predictions=ai_preds,
            race_conditions=[],
            venue="東京",
            total_runners=16,
            cart_items=[],
        )
        assert result["betting_bias"] is not None
        assert isinstance(result["betting_bias"]["biases"], list)

    def test_エラーハンドリング(self):
        """空データでもエラーにならない."""
        result = _analyze_risk_factors_impl(
            race_id="202602010511",
            horse_numbers=[],
            runners_data=[],
            ai_predictions=[],
            race_conditions=[],
            venue="",
            total_runners=0,
            cart_items=[],
        )
        assert "risk_scenarios" in result
        assert "skip_recommendation" in result

    def test_実データ形式の統合テスト(self):
        """実際のデータ形式に近いデータで統合テスト."""
        runners = [
            {"horse_number": 1, "horse_name": "ドウデュース", "odds": 2.5, "popularity": 1},
            {"horse_number": 3, "horse_name": "イクイノックス", "odds": 3.2, "popularity": 2},
            {"horse_number": 5, "horse_name": "リバティアイランド", "odds": 5.0, "popularity": 3},
            {"horse_number": 7, "horse_name": "ソールオリエンス", "odds": 8.5, "popularity": 4},
            {"horse_number": 9, "horse_name": "タスティエーラ", "odds": 12.0, "popularity": 5},
            {"horse_number": 11, "horse_name": "スターズオンアース", "odds": 25.0, "popularity": 6},
            {"horse_number": 13, "horse_name": "ジャスティンパレス", "odds": 35.0, "popularity": 7},
            {"horse_number": 15, "horse_name": "シャフリヤール", "odds": 50.0, "popularity": 8},
        ]
        ai_preds = [
            {"horse_number": 3, "horse_name": "イクイノックス", "rank": 1, "score": 400},
            {"horse_number": 1, "horse_name": "ドウデュース", "rank": 2, "score": 380},
            {"horse_number": 5, "horse_name": "リバティアイランド", "rank": 3, "score": 350},
            {"horse_number": 9, "horse_name": "タスティエーラ", "rank": 4, "score": 300},
            {"horse_number": 7, "horse_name": "ソールオリエンス", "rank": 5, "score": 280},
            {"horse_number": 11, "horse_name": "スターズオンアース", "rank": 6, "score": 250},
            {"horse_number": 13, "horse_name": "ジャスティンパレス", "rank": 7, "score": 200},
            {"horse_number": 15, "horse_name": "シャフリヤール", "rank": 8, "score": 150},
        ]
        result = _analyze_risk_factors_impl(
            race_id="202602010511",
            horse_numbers=[1, 3, 5],
            runners_data=runners,
            ai_predictions=ai_preds,
            race_conditions=["g1"],
            venue="東京",
            total_runners=8,
            cart_items=[
                {"raceId": "202602010511", "betType": "trio",
                 "horseNumbers": [1, 3, 5], "amount": 1000,
                 "runners_data": runners},
            ],
        )
        assert result["risk_scenarios"]["scenarios"]
        assert result["excluded_horses"]["excluded_horses"]
        assert result["skip_recommendation"]["skip_score"] >= 0
