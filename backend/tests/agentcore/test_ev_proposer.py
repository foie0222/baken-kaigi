"""EVベース買い目提案ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.ev_proposer import (
    _propose_bets_impl,
    _make_odds_key,
    _lookup_real_odds,
    _resolve_bet_types,
    _resolve_ev_filter,
    _build_proposal_reasoning,
    DEFAULT_BET_TYPES,
    EV_THRESHOLD,
)


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


def _make_all_odds(runners: list[dict]) -> dict:
    """テスト用の全券種オッズを runners の単勝オッズから生成する."""
    win = {}
    for r in runners:
        hn = r["horse_number"]
        odds = r.get("odds") or 2.0
        win[str(hn)] = odds

    # 連勝式: 関係馬の単勝オッズの積の平方根（簡易推定）
    horse_numbers = sorted(win.keys(), key=lambda x: int(x))
    quinella = {}
    exacta = {}
    quinella_place = {}
    trio = {}
    trifecta = {}

    for i, h1 in enumerate(horse_numbers):
        for j, h2 in enumerate(horse_numbers):
            if j <= i:
                continue
            o1, o2 = win[h1], win[h2]
            geo = (o1 * o2) ** 0.5
            quinella[f"{int(h1)}-{int(h2)}"] = round(geo * 0.85, 1)
            quinella_place[f"{int(h1)}-{int(h2)}"] = round(geo * 0.45, 1)
            exacta[f"{int(h1)}-{int(h2)}"] = round(geo * 1.7, 1)
            exacta[f"{int(h2)}-{int(h1)}"] = round(geo * 1.7, 1)

            for k, h3 in enumerate(horse_numbers):
                if k <= j:
                    continue
                o3 = win[h3]
                geo3 = (o1 * o2 * o3) ** (1 / 3)
                trio[f"{int(h1)}-{int(h2)}-{int(h3)}"] = round(geo3 * 3.0, 1)
                for perm in [
                    (h1, h2, h3), (h1, h3, h2), (h2, h1, h3),
                    (h2, h3, h1), (h3, h1, h2), (h3, h2, h1),
                ]:
                    trifecta[f"{int(perm[0])}-{int(perm[1])}-{int(perm[2])}"] = round(geo3 * 6.0, 1)

    return {
        "win": win,
        "place": {},
        "quinella": quinella,
        "quinella_place": quinella_place,
        "exacta": exacta,
        "trio": trio,
        "trifecta": trifecta,
    }


class TestProposeBetsImpl:
    """_propose_bets_impl のテスト."""

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_EV1以上の買い目だけが選ばれる(self, mock_narrator):
        """確率が高い馬の組合せはEV > 1.0 で選ばれ、低い馬は除外される."""
        runners = _make_runners(6)
        win_probs = {1: 0.50, 2: 0.20, 3: 0.15, 4: 0.08, 5: 0.05, 6: 0.02}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
            all_odds=_make_all_odds(runners),
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
            all_odds=_make_all_odds(runners),
        )

        bets = result["proposed_bets"]
        if len(bets) >= 2:
            for i in range(len(bets) - 1):
                assert bets[i]["expected_value"] >= bets[i + 1]["expected_value"]

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_min_evフィルターでEV未満の組合せが除外される(self, mock_narrator):
        """min_ev=1.0 設定で EV < 1.0 の組合せは除外される."""
        runners = _make_runners(6)
        # 均等な確率 + 低オッズ → EV < 1.0
        win_probs = {i: 1.0 / 6 for i in range(1, 7)}
        for r in runners:
            r["odds"] = 2.0

        from tools.ev_proposer import set_betting_preference
        set_betting_preference({"min_probability": 0.0, "min_ev": 1.0})

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
            all_odds=_make_all_odds(runners),
        )

        assert result["proposed_bets"] == []
        assert result["total_amount"] == 0

        set_betting_preference(None)

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_フィルタ条件を満たす全候補が買い目上限なしで選定される(self, mock_narrator):
        """max_bets 撤廃: フィルタ条件を満たす全候補が上限なしで返される."""
        runners = _make_runners(8)
        win_probs = {1: 0.30, 2: 0.20, 3: 0.15, 4: 0.12, 5: 0.08, 6: 0.06, 7: 0.05, 8: 0.04}

        # min_ev=0.0 で全候補を通過させ、旧上限10件を超えることを検証
        from tools.ev_proposer import set_betting_preference
        set_betting_preference({"min_ev": 0.0})

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=8,
            budget=10000,
            all_odds=_make_all_odds(runners),
        )

        bets = result["proposed_bets"]
        # 旧 DEFAULT_MAX_BETS=10 の上限を超えて全件返される
        assert len(bets) > 10, f"上限撤廃により10件超の候補が返されるべき（実際: {len(bets)}件）"

        set_betting_preference(None)

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
            all_odds=_make_all_odds(runners),
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
            all_odds=_make_all_odds(runners),
        )

        if result["proposed_bets"]:
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
            all_odds=_make_all_odds(runners),
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
        # ProposedBet のフィールド
        if result["proposed_bets"]:
            bet = result["proposed_bets"][0]
            assert "bet_type" in bet
            assert "horse_numbers" in bet
            assert "amount" in bet
            assert "expected_value" in bet
            assert "composite_odds" in bet
            assert "reasoning" in bet
            assert "bet_display" in bet


class TestMakeOddsKey:
    """_make_odds_key のテスト."""

    def test_馬連は昇順キー(self):
        assert _make_odds_key([3, 1], "quinella") == "1-3"

    def test_馬単は着順キー(self):
        assert _make_odds_key([3, 1], "exacta") == "3-1"

    def test_ワイドは昇順キー(self):
        assert _make_odds_key([5, 2], "quinella_place") == "2-5"

    def test_三連複は昇順キー(self):
        assert _make_odds_key([5, 1, 3], "trio") == "1-3-5"

    def test_三連単は着順キー(self):
        assert _make_odds_key([5, 1, 3], "trifecta") == "5-1-3"

    def test_単勝は馬番のみ(self):
        assert _make_odds_key([7], "win") == "7"


class TestLookupRealOdds:
    """_lookup_real_odds のテスト."""

    def test_実オッズを正しく参照できる(self):
        all_odds = {
            "win": {"1": 3.5, "2": 5.8},
            "place": {"1": {"min": 1.2, "max": 1.5}},
            "quinella": {"1-2": 64.8, "1-3": 155.2},
            "exacta": {"1-2": 128.5},
            "quinella_place": {"1-2": 12.3},
            "trio": {"1-2-3": 341.9},
            "trifecta": {"1-2-3": 2048.3},
        }
        assert _lookup_real_odds([1], "win", all_odds) == 3.5
        assert _lookup_real_odds([2, 1], "quinella", all_odds) == 64.8
        assert _lookup_real_odds([1, 2], "exacta", all_odds) == 128.5
        assert _lookup_real_odds([3, 1, 2], "trio", all_odds) == 341.9
        assert _lookup_real_odds([1, 2, 3], "trifecta", all_odds) == 2048.3

    def test_該当組合せなしで0を返す(self):
        all_odds = {"win": {"1": 3.5}, "quinella": {}, "exacta": {},
                    "quinella_place": {}, "trio": {}, "trifecta": {},
                    "place": {}}
        assert _lookup_real_odds([9], "win", all_odds) == 0.0
        assert _lookup_real_odds([1, 2], "quinella", all_odds) == 0.0

    def test_all_oddsが空辞書なら0を返す(self):
        assert _lookup_real_odds([1], "win", {}) == 0.0


class TestProposeBetsImplWithRealOdds:
    """実オッズでのEV計算テスト."""

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_実オッズでEV計算される(self, mock_narrator):
        """all_oddsを渡すと推定オッズでなく実オッズが使われる."""
        runners = _make_runners(4)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.20, 4: 0.15}

        # 馬連1-2のみ高オッズ設定 → EV >= 1.0 になるはず
        all_odds = {
            "win": {"1": 2.5, "2": 4.0, "3": 5.0, "4": 8.0},
            "place": {},
            "quinella": {"1-2": 10.0, "1-3": 3.0, "1-4": 2.0,
                         "2-3": 2.0, "2-4": 2.0, "3-4": 2.0},
            "quinella_place": {},
            "exacta": {},
            "trio": {},
            "trifecta": {},
        }

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=4,
            budget=5000,
            preferred_bet_types=["quinella"],
            all_odds=all_odds,
        )

        bets = result["proposed_bets"]
        # 馬連1-2はEV = prob * 10.0 >= 1.0 のはず
        bet_12 = [b for b in bets if b["horse_numbers"] == [1, 2]]
        assert len(bet_12) == 1
        assert bet_12[0]["composite_odds"] == 10.0

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_horse_numberが文字列でもint型キーになる(self, mock_narrator):
        """runners_data の horse_number が文字列の場合も正しく動作する."""
        runners = [
            {"horse_number": "1", "horse_name": "テスト馬1", "odds": 3.5},
            {"horse_number": "2", "horse_name": "テスト馬2", "odds": 5.8},
        ]
        win_probs = {1: 0.50, 2: 0.30}
        all_odds = {
            "win": {"1": 3.5, "2": 5.8},
            "place": {},
            "quinella": {"1-2": 20.0},
            "quinella_place": {},
            "exacta": {},
            "trio": {},
            "trifecta": {},
        }

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=2,
            budget=5000,
            preferred_bet_types=["quinella"],
            all_odds=all_odds,
        )

        # 文字列horse_numberでもクラッシュせずにint変換される
        bets = result["proposed_bets"]
        if bets:
            assert bets[0]["horse_numbers"] == [1, 2]


# =============================================================================
# 好み設定 → preferred_bet_types 解決テスト
# =============================================================================


class TestResolveBetTypes:
    """_resolve_bet_types のテスト."""

    def test_Noneの場合はデフォルト券種(self):
        assert _resolve_bet_types(None) == DEFAULT_BET_TYPES

    def test_空辞書の場合はデフォルト券種(self):
        assert _resolve_bet_types({}) == DEFAULT_BET_TYPES

    def test_selected_bet_typesが空の場合はデフォルト券種(self):
        assert _resolve_bet_types({"selected_bet_types": []}) == DEFAULT_BET_TYPES

    def test_selected_bet_typesが指定されている場合はそのまま返す(self):
        result = _resolve_bet_types({"selected_bet_types": ["win", "trio"]})
        assert result == ["win", "trio"]

    def test_selected_bet_types単一券種(self):
        result = _resolve_bet_types({"selected_bet_types": ["quinella_place"]})
        assert result == ["quinella_place"]


class TestResolveEvFilter:
    """_resolve_ev_filter のテスト."""

    def test_Noneの場合はデフォルトEV閾値が適用される(self):
        result = _resolve_ev_filter(None)
        assert result == (0.0, 1.0, None, None)

    def test_空辞書の場合はデフォルトEV閾値が適用される(self):
        result = _resolve_ev_filter({})
        assert result == (0.0, 1.0, None, None)

    def test_フィルター値が反映される(self):
        pref = {
            "selected_bet_types": [],
            "min_probability": 0.05,
            "min_ev": 1.5,
            "max_probability": 0.30,
            "max_ev": 5.0,
        }
        result = _resolve_ev_filter(pref)
        assert result == (0.05, 1.5, 0.30, 5.0)

    def test_一部だけ指定の場合は残りデフォルト(self):
        pref = {"min_probability": 0.03}
        result = _resolve_ev_filter(pref)
        assert result == (0.03, 1.0, None, None)

    def test_maxがNoneの場合は上限なし(self):
        pref = {
            "min_probability": 0.05,
            "min_ev": 1.0,
            "max_probability": None,
            "max_ev": None,
        }
        result = _resolve_ev_filter(pref)
        assert result == (0.05, 1.0, None, None)


class TestBuildProposalReasoning:
    """_build_proposal_reasoning のテスト."""

    def test_maxなしの場合は以上表記(self):
        result = _build_proposal_reasoning((0.05, 1.0, None, None), 5)
        assert result == "確率5%以上・期待値1.0以上で5点選定"

    def test_maxありの場合は範囲表記(self):
        result = _build_proposal_reasoning((0.05, 1.0, 0.30, 5.0), 3)
        assert result == "確率5〜30%・期待値1.0〜5.0で3点選定"

    def test_確率maxのみ(self):
        result = _build_proposal_reasoning((0.0, 0.0, 0.20, None), 8)
        assert result == "確率0〜20%・期待値0.0以上で8点選定"


class TestEvFilterIntegration:
    """確率/EVフィルターの統合テスト."""

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_min_probabilityで低確率の組合せが除外される(self, mock_narrator):
        """min_probability=0.20 で確率20%未満の組合せは除外される."""
        runners = _make_runners(4)
        win_probs = {1: 0.50, 2: 0.25, 3: 0.15, 4: 0.10}

        from tools.ev_proposer import set_betting_preference
        set_betting_preference({
            "min_probability": 0.20,
            "min_ev": 0.0,
        })

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=4,
            budget=5000,
            preferred_bet_types=["win"],
            all_odds=_make_all_odds(runners),
        )

        for bet in result["proposed_bets"]:
            assert bet["combination_probability"] >= 0.20

        set_betting_preference(None)

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_min_evで低EV組合せが除外される(self, mock_narrator):
        """min_ev=2.0 で EV < 2.0 の組合せは除外される."""
        runners = _make_runners(6)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}

        from tools.ev_proposer import set_betting_preference
        set_betting_preference({
            "min_probability": 0.0,
            "min_ev": 2.0,
        })

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
            all_odds=_make_all_odds(runners),
        )

        for bet in result["proposed_bets"]:
            assert bet["expected_value"] >= 2.0

        set_betting_preference(None)


class TestRaceBudgetFallback:
    """好み設定の race_budget フォールバックのテスト."""

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_budget未指定時に好み設定のrace_budgetが使われる(self, mock_narrator):
        """budget=0 のとき _current_betting_preference の race_budget を使う."""
        from tools.ev_proposer import set_betting_preference
        set_betting_preference({"race_budget": 5000, "min_ev": 0.0})

        runners = _make_runners(4)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.20, 4: 0.15}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=4,
            budget=0,
            all_odds=_make_all_odds(runners),
        )

        assert result["total_amount"] > 0

        set_betting_preference(None)

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_budgetが明示指定されていればrace_budgetは使われない(self, mock_narrator):
        """budget > 0 のときは好み設定の race_budget より明示budgetが優先."""
        from tools.ev_proposer import set_betting_preference
        set_betting_preference({"race_budget": 10000, "min_ev": 0.0})

        runners = _make_runners(4)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.20, 4: 0.15}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=4,
            budget=3000,
            all_odds=_make_all_odds(runners),
        )

        # 3000円予算で配分される（10000円ではない）
        assert result["total_amount"] <= 3000

        set_betting_preference(None)

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_好み設定なしでbudget0なら金額0(self, mock_narrator):
        """好み設定がなくbudget=0の場合はtotal_amount=0."""
        from tools.ev_proposer import set_betting_preference
        set_betting_preference(None)

        runners = _make_runners(4)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.20, 4: 0.15}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=4,
            budget=0,
            all_odds=_make_all_odds(runners),
        )

        assert result["total_amount"] == 0
