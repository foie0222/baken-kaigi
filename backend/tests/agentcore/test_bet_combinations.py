"""馬券組み合わせツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.bet_combinations import (
        suggest_bet_combinations,
        _calculate_horse_scores,
        _select_partners,
        _identify_excluded_horses,
        _generate_bet_suggestions,
        _allocate_budget,
        BASE_SCORE,
        SCORE_DELTA_STYLE,
        SCORE_DELTA_INNER_GATE,
        SCORE_DELTA_OUTER_GATE,
        SCORE_HIGH_CONFIDENCE,
        SCORE_MEDIUM_CONFIDENCE,
        MAX_HIGH_CONFIDENCE,
        MAX_EXCLUDED_HORSES,
        MAX_BET_SUGGESTIONS,
        MIN_BET_AMOUNT,
    )
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_dynamodb_client():
    """DynamoDBクライアントをモック化."""
    with patch("tools.bet_combinations.dynamodb_client") as mock_client:
        mock_client.get_runners.return_value = []
        mock_client.get_horse_performances.return_value = []
        yield mock_client


def _make_runners(count=6):
    """テスト用出走馬リストを生成する."""
    return [
        {"horse_number": i + 1, "horse_id": f"horse_{i + 1}", "horse_name": f"テスト馬{i + 1}"}
        for i in range(count)
    ]


def _make_running_styles(styles_map):
    """テスト用脚質データを生成する.

    Args:
        styles_map: {horse_number: running_style} の辞書
    """
    return [
        {"horse_number": num, "running_style": style}
        for num, style in styles_map.items()
    ]


class TestSuggestBetCombinations:
    """馬券組み合わせ統合テスト."""

    def test_正常系_馬券組み合わせを提案(self, mock_dynamodb_client):
        """正常系: 馬券組み合わせを正しく提案できる."""
        mock_dynamodb_client.get_runners.return_value = [
            {"horse_number": 1, "horse_id": "h1", "odds": 2.5, "popularity": 1},
            {"horse_number": 2, "horse_id": "h2", "odds": 5.0, "popularity": 2},
            {"horse_number": 3, "horse_id": "h3", "odds": 10.0, "popularity": 3},
        ]
        mock_dynamodb_client.get_horse_performances.return_value = []

        result = suggest_bet_combinations(
            race_id="20260125_06_11",
            axis_horses=[1],
            bet_type="馬連",
            budget=1000,
        )

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    def test_Exception時にエラーを返す(self, mock_dynamodb_client):
        """異常系: Exception発生時はerrorを返す."""
        mock_dynamodb_client.get_runners.side_effect = Exception("Connection failed")

        result = suggest_bet_combinations(
            race_id="20260125_06_11",
            axis_horses=[1],
            bet_type="馬連",
            budget=1000,
        )

        assert "error" in result


class TestCalculateHorseScores:
    """_calculate_horse_scores のテスト."""

    @patch("tools.bet_combinations._evaluate_form", return_value=(0, [], []))
    def test_基本スコアが50で初期化される(self, mock_form, mock_dynamodb_client):
        """脚質・枠順の補正がない場合、基本スコアはBASE_SCORE."""
        runners = [{"horse_number": 8, "horse_id": "h1", "horse_name": "テスト馬"}]
        styles = []

        scores = _calculate_horse_scores(runners, styles)

        assert scores[8]["score"] == BASE_SCORE

    @patch("tools.bet_combinations._evaluate_form", return_value=(0, [], []))
    def test_先行脚質でスコアが加算される(self, mock_form, mock_dynamodb_client):
        """先行脚質の馬はスコアが+5される."""
        runners = [{"horse_number": 8, "horse_id": "h1"}]
        styles = _make_running_styles({8: "先行"})

        scores = _calculate_horse_scores(runners, styles)

        assert scores[8]["score"] == BASE_SCORE + SCORE_DELTA_STYLE
        assert "脚質良好" in scores[8]["reasons"]

    @patch("tools.bet_combinations._evaluate_form", return_value=(0, [], []))
    def test_差し脚質でスコアが加算される(self, mock_form, mock_dynamodb_client):
        """差し脚質の馬はスコアが+5される."""
        runners = [{"horse_number": 8, "horse_id": "h1"}]
        styles = _make_running_styles({8: "差し"})

        scores = _calculate_horse_scores(runners, styles)

        assert scores[8]["score"] == BASE_SCORE + SCORE_DELTA_STYLE

    @patch("tools.bet_combinations._evaluate_form", return_value=(0, [], []))
    def test_追込脚質でリスク理由が追加される(self, mock_form, mock_dynamodb_client):
        """追込脚質の馬はリスク理由に追加される."""
        runners = [{"horse_number": 8, "horse_id": "h1"}]
        styles = _make_running_styles({8: "追込"})

        scores = _calculate_horse_scores(runners, styles)

        assert scores[8]["score"] == BASE_SCORE
        assert "追込脚質" in scores[8]["risk_reasons"]

    @patch("tools.bet_combinations._evaluate_form", return_value=(0, [], []))
    def test_内枠でスコアが加算される(self, mock_form, mock_dynamodb_client):
        """馬番4以下の内枠はスコアが+5される."""
        runners = [{"horse_number": 3, "horse_id": "h1"}]
        styles = []

        scores = _calculate_horse_scores(runners, styles)

        assert scores[3]["score"] == BASE_SCORE + SCORE_DELTA_INNER_GATE
        assert "内枠有利" in scores[3]["reasons"]

    @patch("tools.bet_combinations._evaluate_form", return_value=(0, [], []))
    def test_外枠でスコアが減算される(self, mock_form, mock_dynamodb_client):
        """馬番14以上の外枠はスコアが-5される."""
        runners = [{"horse_number": 15, "horse_id": "h1"}]
        styles = []

        scores = _calculate_horse_scores(runners, styles)

        assert scores[15]["score"] == BASE_SCORE + SCORE_DELTA_OUTER_GATE
        assert "外枠不利" in scores[15]["risk_reasons"]

    @patch("tools.bet_combinations._evaluate_form", return_value=(20, ["好成績継続"], []))
    def test_過去成績のスコアが反映される(self, mock_form, mock_dynamodb_client):
        """_evaluate_formの結果がスコアに反映される."""
        runners = [{"horse_number": 8, "horse_id": "h1"}]
        styles = []

        scores = _calculate_horse_scores(runners, styles)

        assert scores[8]["score"] == BASE_SCORE + 20
        assert "好成績継続" in scores[8]["reasons"]

    @patch("tools.bet_combinations._evaluate_form", return_value=(0, [], []))
    def test_スコアは0から100の範囲に収まる(self, mock_form, mock_dynamodb_client):
        """スコアは0未満や100超えにはならない."""
        # 内枠(+5) + 先行(+5) でも100を超えないことを確認
        mock_form.return_value = (60, ["好成績"], [])
        runners = [{"horse_number": 1, "horse_id": "h1"}]
        styles = _make_running_styles({1: "先行"})

        scores = _calculate_horse_scores(runners, styles)

        assert scores[1]["score"] <= 100

    @patch("tools.bet_combinations._evaluate_form", return_value=(-60, [], ["成績不振"]))
    def test_スコアは0未満にならない(self, mock_form, mock_dynamodb_client):
        """スコアは0未満にならない."""
        runners = [{"horse_number": 15, "horse_id": "h1"}]
        styles = _make_running_styles({15: "追込"})

        scores = _calculate_horse_scores(runners, styles)

        assert scores[15]["score"] >= 0


class TestSelectPartners:
    """_select_partners のテスト."""

    def test_高スコア馬がhigh_confidenceに分類される(self):
        """スコア75以上の馬はhigh_confidenceに分類される."""
        runners = _make_runners(4)
        horse_scores = {
            1: {"score": 80, "reasons": ["好成績"], "risk_reasons": []},
            2: {"score": 90, "reasons": ["好成績", "脚質良好"], "risk_reasons": []},
            3: {"score": 60, "reasons": ["安定"], "risk_reasons": []},
            4: {"score": 40, "reasons": [], "risk_reasons": ["不振"]},
        }
        odds_data = {1: 3.0, 2: 4.0, 3: 8.0, 4: 15.0}

        partners = _select_partners([1], runners, horse_scores, odds_data)

        high_numbers = [p["number"] for p in partners["high_confidence"]]
        assert 2 in high_numbers

    def test_中スコア馬がmedium_confidenceに分類される(self):
        """スコア60以上75未満の馬はmedium_confidenceに分類される."""
        runners = _make_runners(3)
        horse_scores = {
            1: {"score": 80, "reasons": ["好成績"], "risk_reasons": []},
            2: {"score": 65, "reasons": ["安定"], "risk_reasons": []},
            3: {"score": 70, "reasons": ["安定"], "risk_reasons": []},
        }
        odds_data = {1: 3.0, 2: 8.0, 3: 6.0}

        partners = _select_partners([1], runners, horse_scores, odds_data)

        medium_numbers = [p["number"] for p in partners["medium_confidence"]]
        assert 2 in medium_numbers
        assert 3 in medium_numbers

    def test_穴馬がvalue_picksに分類される(self):
        """スコア45以上かつオッズ10以上の馬はvalue_picksに分類される."""
        runners = _make_runners(3)
        horse_scores = {
            1: {"score": 80, "reasons": ["好成績"], "risk_reasons": []},
            2: {"score": 50, "reasons": ["データ不足"], "risk_reasons": []},
            3: {"score": 30, "reasons": [], "risk_reasons": ["不振"]},
        }
        odds_data = {1: 3.0, 2: 15.0, 3: 50.0}

        partners = _select_partners([1], runners, horse_scores, odds_data)

        value_numbers = [p["number"] for p in partners["value_picks"]]
        assert 2 in value_numbers

    def test_軸馬は相手馬候補に含まれない(self):
        """軸馬自身は相手馬候補から除外される."""
        runners = _make_runners(3)
        horse_scores = {
            1: {"score": 90, "reasons": ["好成績"], "risk_reasons": []},
            2: {"score": 80, "reasons": ["好成績"], "risk_reasons": []},
            3: {"score": 70, "reasons": ["安定"], "risk_reasons": []},
        }
        odds_data = {1: 2.0, 2: 4.0, 3: 8.0}

        partners = _select_partners([1], runners, horse_scores, odds_data)

        all_partner_numbers = (
            [p["number"] for p in partners["high_confidence"]]
            + [p["number"] for p in partners["medium_confidence"]]
            + [p["number"] for p in partners["value_picks"]]
        )
        assert 1 not in all_partner_numbers

    def test_high_confidenceはスコア降順でソートされる(self):
        """high_confidenceはスコアの高い順にソートされる."""
        runners = _make_runners(5)
        horse_scores = {
            1: {"score": 90, "reasons": ["好成績"], "risk_reasons": []},
            2: {"score": 80, "reasons": ["好成績"], "risk_reasons": []},
            3: {"score": 85, "reasons": ["好成績"], "risk_reasons": []},
            4: {"score": 76, "reasons": ["好成績"], "risk_reasons": []},
            5: {"score": 78, "reasons": ["好成績"], "risk_reasons": []},
        }
        odds_data = {}

        partners = _select_partners([1], runners, horse_scores, odds_data)

        high_scores = [p["score"] for p in partners["high_confidence"]]
        assert high_scores == sorted(high_scores, reverse=True)

    def test_各カテゴリの最大件数が制限される(self):
        """各カテゴリの件数が定数で制限される."""
        runners = _make_runners(16)
        horse_scores = {
            i: {"score": 90, "reasons": ["好成績"], "risk_reasons": []}
            for i in range(1, 17)
        }
        odds_data = {}

        partners = _select_partners([1], runners, horse_scores, odds_data)

        assert len(partners["high_confidence"]) <= MAX_HIGH_CONFIDENCE


class TestIdentifyExcludedHorses:
    """_identify_excluded_horses のテスト."""

    def test_低スコア馬が消し馬に含まれる(self):
        """スコアがSCORE_VALUE_PICK未満の馬は消し馬になる."""
        runners = _make_runners(3)
        horse_scores = {
            1: {"score": 80, "reasons": ["好成績"], "risk_reasons": []},
            2: {"score": 30, "reasons": [], "risk_reasons": ["成績不振"]},
            3: {"score": 60, "reasons": ["安定"], "risk_reasons": []},
        }
        odds_data = {}

        excluded = _identify_excluded_horses([1], runners, horse_scores, odds_data)

        excluded_numbers = [e["number"] for e in excluded]
        assert 2 in excluded_numbers

    def test_人気なのにスコアが低い馬が消し馬になる(self):
        """オッズ5.0以下で中スコア未満の馬は消し馬になる."""
        runners = _make_runners(3)
        horse_scores = {
            1: {"score": 80, "reasons": ["好成績"], "risk_reasons": []},
            2: {"score": 55, "reasons": [], "risk_reasons": ["過剰人気"]},
            3: {"score": 70, "reasons": ["安定"], "risk_reasons": []},
        }
        odds_data = {1: 2.0, 2: 3.0, 3: 8.0}

        excluded = _identify_excluded_horses([1], runners, horse_scores, odds_data)

        excluded_numbers = [e["number"] for e in excluded]
        assert 2 in excluded_numbers

    def test_軸馬は消し馬に含まれない(self):
        """軸馬は消し馬候補から除外される."""
        runners = _make_runners(2)
        horse_scores = {
            1: {"score": 30, "reasons": [], "risk_reasons": ["不振"]},
            2: {"score": 30, "reasons": [], "risk_reasons": ["不振"]},
        }
        odds_data = {}

        excluded = _identify_excluded_horses([1], runners, horse_scores, odds_data)

        excluded_numbers = [e["number"] for e in excluded]
        assert 1 not in excluded_numbers

    def test_risk_levelが正しく設定される(self):
        """スコアがSCORE_EXCLUDE_CRITICAL未満なら消し推奨、それ以上なら注意."""
        runners = _make_runners(3)
        horse_scores = {
            1: {"score": 80, "reasons": [], "risk_reasons": []},
            2: {"score": 35, "reasons": [], "risk_reasons": ["不振"]},  # < 40 -> 消し推奨
            3: {"score": 42, "reasons": [], "risk_reasons": ["不振"]},  # >= 40, < 45 -> 注意
        }
        odds_data = {}

        excluded = _identify_excluded_horses([1], runners, horse_scores, odds_data)

        excluded_map = {e["number"]: e for e in excluded}
        assert excluded_map[2]["risk_level"] == "消し推奨"
        assert excluded_map[3]["risk_level"] == "注意"

    def test_消し馬リストがスコア昇順にソートされる(self):
        """消し馬はスコアが低い順（昇順）にソートされるべき."""
        runners = _make_runners(5)
        horse_scores = {
            1: {"score": 80, "reasons": [], "risk_reasons": []},
            2: {"score": 40, "reasons": [], "risk_reasons": ["不振"]},
            3: {"score": 20, "reasons": [], "risk_reasons": ["大不振"]},
            4: {"score": 35, "reasons": [], "risk_reasons": ["不安定"]},
            5: {"score": 10, "reasons": [], "risk_reasons": ["危険"]},
        }
        odds_data = {}

        excluded = _identify_excluded_horses([1], runners, horse_scores, odds_data)

        # スコアが低い順にソートされているべき
        scores = [horse_scores[e["number"]]["score"] for e in excluded]
        assert scores == sorted(scores), f"消し馬がスコア昇順にソートされていない: {scores}"

    def test_消し馬リストは最大件数に制限される(self):
        """消し馬リストはMAX_EXCLUDED_HORSES件に制限される."""
        runners = _make_runners(10)
        horse_scores = {
            i: {"score": 10 + i, "reasons": [], "risk_reasons": ["不振"]}
            for i in range(1, 11)
        }
        odds_data = {}

        excluded = _identify_excluded_horses([1], runners, horse_scores, odds_data)

        assert len(excluded) <= MAX_EXCLUDED_HORSES


class TestGenerateBetSuggestions:
    """_generate_bet_suggestions のテスト."""

    def _make_partners(self, numbers_and_scores):
        """テスト用相手馬データを生成する."""
        high = []
        medium = []
        value = []
        for num, score in numbers_and_scores:
            partner = {
                "number": num,
                "name": f"テスト馬{num}",
                "score": score,
                "reasons": ["テスト"],
                "odds_value": "適正",
            }
            if score >= SCORE_HIGH_CONFIDENCE:
                high.append(partner)
            elif score >= SCORE_MEDIUM_CONFIDENCE:
                medium.append(partner)
            else:
                value.append(partner)
        return {
            "high_confidence": high,
            "medium_confidence": medium,
            "value_picks": value,
        }

    def test_馬連の買い目が正しい形式で生成される(self):
        """馬連は小さい番号-大きい番号の形式."""
        partners = self._make_partners([(3, 80)])
        odds_data = {1: 3.0, 3: 5.0}

        suggestions = _generate_bet_suggestions([1], partners, "馬連", odds_data, 10000)

        assert len(suggestions) > 0
        assert suggestions[0]["combination"] == "1-3"
        assert suggestions[0]["bet_type"] == "馬連"

    def test_馬単の買い目が軸馬を先にする(self):
        """馬単は軸馬-相手馬の順序."""
        partners = self._make_partners([(2, 80)])
        odds_data = {5: 3.0, 2: 5.0}

        suggestions = _generate_bet_suggestions([5], partners, "馬単", odds_data, 10000)

        assert suggestions[0]["combination"] == "5-2"

    def test_ワイドの買い目が正しい形式で生成される(self):
        """ワイドは小さい番号-大きい番号の形式."""
        partners = self._make_partners([(2, 80)])
        odds_data = {5: 3.0, 2: 5.0}

        suggestions = _generate_bet_suggestions([5], partners, "ワイド", odds_data, 10000)

        assert suggestions[0]["combination"] == "2-5"

    def test_3連複の買い目が3頭の組み合わせになる(self):
        """3連複は軸馬と相手馬2頭の3頭組み合わせが必要."""
        partners = self._make_partners([(3, 80), (5, 70), (7, 50)])
        odds_data = {1: 3.0, 3: 5.0, 5: 8.0, 7: 15.0}

        suggestions = _generate_bet_suggestions([1], partners, "3連複", odds_data, 10000)

        assert len(suggestions) > 0
        for s in suggestions:
            parts = s["combination"].split("-")
            assert len(parts) == 3, f"3連複の組み合わせが3頭でない: {s['combination']}"

    def test_3連単の買い目が3頭の組み合わせになる(self):
        """3連単は軸馬と相手馬2頭の3頭組み合わせが必要."""
        partners = self._make_partners([(3, 80), (5, 70), (7, 50)])
        odds_data = {1: 3.0, 3: 5.0, 5: 8.0, 7: 15.0}

        suggestions = _generate_bet_suggestions([1], partners, "3連単", odds_data, 10000)

        assert len(suggestions) > 0
        for s in suggestions:
            parts = s["combination"].split("-")
            assert len(parts) == 3, f"3連単の組み合わせが3頭でない: {s['combination']}"

    def test_3連複の組み合わせが番号昇順になる(self):
        """3連複は小さい番号順に並ぶべき."""
        partners = self._make_partners([(3, 80), (5, 70)])
        odds_data = {1: 3.0, 3: 5.0, 5: 8.0}

        suggestions = _generate_bet_suggestions([1], partners, "3連複", odds_data, 10000)

        for s in suggestions:
            parts = [int(p) for p in s["combination"].split("-")]
            assert parts == sorted(parts), f"3連複が番号順でない: {s['combination']}"

    def test_3連単の組み合わせが軸馬を先頭にする(self):
        """3連単は軸馬が先頭になるべき."""
        partners = self._make_partners([(3, 80), (5, 70)])
        odds_data = {1: 3.0, 3: 5.0, 5: 8.0}

        suggestions = _generate_bet_suggestions([1], partners, "3連単", odds_data, 10000)

        for s in suggestions:
            parts = s["combination"].split("-")
            assert parts[0] == "1", f"3連単の先頭が軸馬でない: {s['combination']}"

    def test_信頼度に応じた金額配分(self):
        """高スコア馬は高い金額、低スコア馬は低い金額が配分される."""
        partners = self._make_partners([(3, 80), (5, 50)])
        odds_data = {1: 3.0, 3: 5.0, 5: 15.0}

        suggestions = _generate_bet_suggestions([1], partners, "馬連", odds_data, 10000)

        high_bet = [s for s in suggestions if s["confidence"] == "高"]
        value_bet = [s for s in suggestions if "穴" in s["confidence"]]
        if high_bet and value_bet:
            assert high_bet[0]["suggested_amount"] > value_bet[0]["suggested_amount"]

    def test_最低賭け金額が100円以上(self):
        """提案金額は最低100円以上."""
        partners = self._make_partners([(3, 50)])
        odds_data = {1: 3.0, 3: 15.0}

        suggestions = _generate_bet_suggestions([1], partners, "馬連", odds_data, 100)

        for s in suggestions:
            assert s["suggested_amount"] >= MIN_BET_AMOUNT

    def test_最大提案数が制限される(self):
        """提案数はMAX_BET_SUGGESTIONS以下."""
        partners = self._make_partners(
            [(i, 80) for i in range(2, 12)]
        )
        odds_data = {i: 5.0 for i in range(1, 12)}

        suggestions = _generate_bet_suggestions([1], partners, "馬連", odds_data, 10000)

        assert len(suggestions) <= MAX_BET_SUGGESTIONS


class TestAllocateBudget:
    """_allocate_budget のテスト."""

    def test_全カテゴリに相手馬がいる場合の配分(self):
        """全カテゴリに相手馬がいる場合、定義比率で配分される."""
        partners = {
            "high_confidence": [{"number": 2}],
            "medium_confidence": [{"number": 3}],
            "value_picks": [{"number": 4}],
        }

        allocation = _allocate_budget(10000, partners)

        assert allocation["total_budget"] == 10000
        assert allocation["high_confidence_allocation"] > 0
        assert allocation["medium_confidence_allocation"] > 0
        assert allocation["value_allocation"] > 0
        total = (
            allocation["high_confidence_allocation"]
            + allocation["medium_confidence_allocation"]
            + allocation["value_allocation"]
        )
        assert total == 10000

    def test_high_confidenceのみの場合に全額配分される(self):
        """high_confidenceのみの場合、残額含め全額がhighに配分される."""
        partners = {
            "high_confidence": [{"number": 2}],
            "medium_confidence": [],
            "value_picks": [],
        }

        allocation = _allocate_budget(10000, partners)

        assert allocation["high_confidence_allocation"] == 10000
        assert allocation["medium_confidence_allocation"] == 0
        assert allocation["value_allocation"] == 0

    def test_相手馬がいない場合は全て0配分(self):
        """相手馬が全くいない場合は全カテゴリ0."""
        partners = {
            "high_confidence": [],
            "medium_confidence": [],
            "value_picks": [],
        }

        allocation = _allocate_budget(10000, partners)

        assert allocation["high_confidence_allocation"] == 0
        assert allocation["medium_confidence_allocation"] == 0
        assert allocation["value_allocation"] == 0
        assert allocation["total_budget"] == 10000

    def test_medium_confidenceのみの場合(self):
        """medium_confidenceのみの場合、残額がmediumに配分される."""
        partners = {
            "high_confidence": [],
            "medium_confidence": [{"number": 3}],
            "value_picks": [],
        }

        allocation = _allocate_budget(10000, partners)

        assert allocation["high_confidence_allocation"] == 0
        assert allocation["medium_confidence_allocation"] == 10000
        assert allocation["value_allocation"] == 0

    def test_value_picksのみの場合(self):
        """value_picksのみの場合、残額がvalueに配分される."""
        partners = {
            "high_confidence": [],
            "medium_confidence": [],
            "value_picks": [{"number": 4}],
        }

        allocation = _allocate_budget(10000, partners)

        assert allocation["high_confidence_allocation"] == 0
        assert allocation["medium_confidence_allocation"] == 0
        assert allocation["value_allocation"] == 10000

    def test_配分合計が予算と一致する(self):
        """配分合計は常に予算と一致する."""
        partners = {
            "high_confidence": [{"number": 2}, {"number": 3}],
            "medium_confidence": [{"number": 4}],
            "value_picks": [{"number": 5}],
        }

        allocation = _allocate_budget(7777, partners)

        total = (
            allocation["high_confidence_allocation"]
            + allocation["medium_confidence_allocation"]
            + allocation["value_allocation"]
        )
        assert total == 7777
