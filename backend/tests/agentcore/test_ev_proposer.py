"""EVベース買い目提案ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.ev_proposer import _propose_bets_impl


def _make_runners(count: int) -> list[dict]:
    """テスト用出走馬データを生成する."""
    runners = []
    for i in range(1, count + 1):
        runners.append({
            "horse_number": i,
            "horse_name": f"テスト馬{i}",
            "popularity": i,
            "odds": round(2.0 + i * 1.5, 1),
        })
    return runners


class TestProposeBetsImpl:
    """_propose_bets_impl のテスト."""

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_EV1以上の買い目だけが選ばれる(self, mock_narrator):
        """確率が高い馬の組合せはEV > 1.0 で選ばれ、低い馬は除外される."""
        runners = _make_runners(6)
        # 馬1が圧倒的に強い → 馬1絡みの組合せのEVが高い
        win_probs = {1: 0.50, 2: 0.20, 3: 0.15, 4: 0.08, 5: 0.05, 6: 0.02}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
        )

        assert "proposed_bets" in result
        for bet in result["proposed_bets"]:
            assert bet["expected_value"] >= 1.0

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_EV降順にソートされる(self, mock_narrator):
        runners = _make_runners(6)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
        )

        bets = result["proposed_bets"]
        if len(bets) >= 2:
            for i in range(len(bets) - 1):
                assert bets[i]["expected_value"] >= bets[i + 1]["expected_value"]

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_全組合せEV1未満で買い目ゼロ(self, mock_narrator):
        """確率が低くオッズも低い→全てEV < 1.0 → 買い目なし."""
        runners = _make_runners(6)
        # 均等な確率 + 低オッズ → EV < 1.0
        win_probs = {i: 1.0 / 6 for i in range(1, 7)}
        # オッズを全部低くする
        for r in runners:
            r["odds"] = 2.0

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
        )

        assert result["proposed_bets"] == []
        assert result["total_amount"] == 0

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_max_betsで買い目数が制限される(self, mock_narrator):
        runners = _make_runners(8)
        win_probs = {1: 0.35, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.05, 6: 0.04, 7: 0.03, 8: 0.03}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=8,
            budget=10000,
            max_bets=3,
        )

        assert len(result["proposed_bets"]) <= 3

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_preferred_bet_typesで券種がフィルタされる(self, mock_narrator):
        runners = _make_runners(6)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
            preferred_bet_types=["quinella"],
        )

        for bet in result["proposed_bets"]:
            assert bet["bet_type"] == "quinella"

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_bankrollモードでダッチング配分(self, mock_narrator):
        runners = _make_runners(6)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            bankroll=100000,
        )

        if result["proposed_bets"]:
            assert "confidence_factor" in result
            assert "race_budget" in result

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_フロントエンド互換の出力形式(self, mock_narrator):
        """BetProposalResponse 型に合致する構造を返すこと."""
        runners = _make_runners(6)
        win_probs = {1: 0.50, 2: 0.20, 3: 0.15, 4: 0.08, 5: 0.05, 6: 0.02}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
            race_name="テスト重賞",
            race_conditions=["芝", "良"],
            venue="東京",
        )

        # BetProposalResponse の必須フィールド
        assert "race_id" in result
        assert "race_summary" in result
        assert "proposed_bets" in result
        assert "total_amount" in result
        assert "budget_remaining" in result
        assert "analysis_comment" in result
        assert "disclaimer" in result

        # RaceSummary のフィールド
        summary = result["race_summary"]
        assert "race_name" in summary
        assert "difficulty_stars" in summary

        # ProposedBet のフィールド
        if result["proposed_bets"]:
            bet = result["proposed_bets"][0]
            assert "bet_type" in bet
            assert "horse_numbers" in bet
            assert "amount" in bet
            assert "confidence" in bet
            assert "expected_value" in bet
            assert "composite_odds" in bet
            assert "reasoning" in bet
            assert "bet_display" in bet
