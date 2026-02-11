"""総合レース分析ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.race_comprehensive_analysis import (
        analyze_race_comprehensive,
        _evaluate_form_from_performances,
        _evaluate_course_aptitude,
        _evaluate_jockey,
        _evaluate_body_weight,
        _calculate_overall_score,
        _predict_race_scenario,
        _identify_notable_horses,
        _generate_betting_suggestion,
        _evaluate_race_quality,
    )
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


# =============================================================================
# テスト用データ
# =============================================================================

def _make_performances(positions: list[int]) -> list[dict]:
    """テスト用過去成績データを生成する."""
    return [{"finish_position": pos} for pos in positions]


def _make_running_styles(styles: list[tuple[int, str, str]]) -> list[dict]:
    """テスト用脚質データを生成する.

    Args:
        styles: (馬番, 馬名, 脚質) のリスト
    """
    return [
        {"horse_number": num, "horse_name": name, "running_style": style}
        for num, name, style in styles
    ]


def _make_runner_evaluation(
    horse_number: int,
    horse_name: str,
    overall_score: int,
    rank: int,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
) -> dict:
    """テスト用出走馬評価データを生成する."""
    return {
        "horse_number": horse_number,
        "horse_name": horse_name,
        "overall_score": overall_score,
        "rank": rank,
        "strengths": strengths or [],
        "weaknesses": weaknesses or [],
        "key_factors": {},
    }


# =============================================================================
# テスト用fixture
# =============================================================================

@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.race_comprehensive_analysis.get_headers", return_value={"x-api-key": "test-key"}):
        with patch("tools.race_comprehensive_analysis.get_api_url", return_value="https://api.example.com"):
            yield


# =============================================================================
# 統合テスト
# =============================================================================


class TestAnalyzeRaceComprehensive:
    """総合レース分析統合テスト."""

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_正常系_レースを総合分析(self, mock_get):
        """正常系: レースデータを総合的に分析できる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "race": {
                "race_name": "テストレース",
                "distance": 1600,
                "track_type": "芝",
            },
            "runners": [
                {"horse_number": 1, "horse_name": "馬1", "odds": 2.5},
                {"horse_number": 2, "horse_name": "馬2", "odds": 5.0},
            ],
        }
        mock_get.return_value = mock_response

        result = analyze_race_comprehensive(race_id="20260125_06_11")

        # 正常系では明示的にerrorがないことを確認
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = analyze_race_comprehensive(race_id="20260125_06_11")

        assert "error" in result


# =============================================================================
# _evaluate_form_from_performances テスト
# =============================================================================


class TestEvaluateFormFromPerformances:
    """過去成績からのフォーム評価テスト."""

    def test_空リストはC評価(self):
        """成績なし → C."""
        assert _evaluate_form_from_performances([]) == "C"

    def test_着順が全て0の場合はC評価(self):
        """finish_positionが全て0 → finishesが空 → C."""
        performances = [{"finish_position": 0}, {"finish_position": 0}]
        assert _evaluate_form_from_performances(performances) == "C"

    def test_finish_positionキーなしはC評価(self):
        """finish_positionキーがない → 0扱いで除外 → C."""
        performances = [{}, {}]
        assert _evaluate_form_from_performances(performances) == "C"

    def test_好成績でA評価(self):
        """平均3.0以下かつ3着以内3回以上 → A."""
        # 1, 2, 3, 2, 1 → avg=1.8, in_money=5
        performances = _make_performances([1, 2, 3, 2, 1])
        assert _evaluate_form_from_performances(performances) == "A"

    def test_A評価の境界_平均ちょうど3で複勝3回(self):
        """平均=3.0, in_money=3 → A."""
        # 1, 2, 3, 3, 6 → avg=3.0, in_money=4
        performances = _make_performances([1, 2, 3, 3, 6])
        assert _evaluate_form_from_performances(performances) == "A"

    def test_中程度でB評価(self):
        """平均5.0以下かつ3着以内2回以上 → B."""
        # 2, 3, 5, 7, 5 → avg=4.4, in_money=2
        performances = _make_performances([2, 3, 5, 7, 5])
        assert _evaluate_form_from_performances(performances) == "B"

    def test_B評価の境界_平均ちょうど5で複勝2回(self):
        """平均=5.0, in_money=2 → B."""
        # 1, 3, 6, 7, 8 → avg=5.0, in_money=2
        performances = _make_performances([1, 3, 6, 7, 8])
        assert _evaluate_form_from_performances(performances) == "B"

    def test_低成績でC評価(self):
        """平均5超 → C."""
        # 8, 10, 12 → avg=10.0, in_money=0
        performances = _make_performances([8, 10, 12])
        assert _evaluate_form_from_performances(performances) == "C"

    def test_平均は低いが複勝回数不足でB(self):
        """平均3.0以下だがin_money<3 → Bに落ちる."""
        # 1, 2, 8 → avg=3.67 → 3.0超なのでB条件チェック
        # avg=3.67, in_money=2 → B
        performances = _make_performances([1, 2, 8])
        assert _evaluate_form_from_performances(performances) == "B"

    def test_平均低いが複勝1回ではC(self):
        """平均5超、in_money=1 → C."""
        # 3, 8, 10 → avg=7.0, in_money=1
        performances = _make_performances([3, 8, 10])
        assert _evaluate_form_from_performances(performances) == "C"

    def test_1レースのみで1着はB(self):
        """1レースだけで1着 → avg=1.0, in_money=1 → B条件(avg<=5, in_money>=2)を満たさない.
        A条件(avg<=3, in_money>=3)も不可 → C."""
        performances = _make_performances([1])
        # avg=1.0, in_money=1 → B条件 in_money>=2 不満足 → C
        assert _evaluate_form_from_performances(performances) == "C"


# =============================================================================
# _evaluate_course_aptitude テスト
# =============================================================================


class TestEvaluateCourseAptitude:
    """コース適性評価テスト."""

    def test_venue_statsが空ならB(self):
        """該当競馬場のデータなし → B."""
        data = {"venue_stats": {}}
        assert _evaluate_course_aptitude(data, "東京") == "B"

    def test_venue_statsキーなしならB(self):
        """venue_statsキー自体なし → B."""
        data = {}
        assert _evaluate_course_aptitude(data, "東京") == "B"

    def test_該当会場のデータなしならB(self):
        """別の会場のデータしかない → B."""
        data = {"venue_stats": {"中山": {"win_rate": 30, "in_money_rate": 60}}}
        assert _evaluate_course_aptitude(data, "東京") == "B"

    def test_勝率20以上でA評価(self):
        """win_rate >= 20 → A."""
        data = {"venue_stats": {"東京": {"win_rate": 20, "in_money_rate": 40}}}
        assert _evaluate_course_aptitude(data, "東京") == "A"

    def test_複勝率50以上でA評価(self):
        """in_money_rate >= 50 → A."""
        data = {"venue_stats": {"東京": {"win_rate": 10, "in_money_rate": 50}}}
        assert _evaluate_course_aptitude(data, "東京") == "A"

    def test_勝率10以上20未満でB評価(self):
        """10 <= win_rate < 20, in_money_rate < 50 → B."""
        data = {"venue_stats": {"東京": {"win_rate": 15, "in_money_rate": 40}}}
        assert _evaluate_course_aptitude(data, "東京") == "B"

    def test_複勝率30以上50未満でB評価(self):
        """win_rate < 10, 30 <= in_money_rate < 50 → B."""
        data = {"venue_stats": {"東京": {"win_rate": 5, "in_money_rate": 35}}}
        assert _evaluate_course_aptitude(data, "東京") == "B"

    def test_勝率低く複勝率も低いとC評価(self):
        """win_rate < 10, in_money_rate < 30 → C."""
        data = {"venue_stats": {"東京": {"win_rate": 5, "in_money_rate": 20}}}
        assert _evaluate_course_aptitude(data, "東京") == "C"

    def test_全てゼロはC評価(self):
        """win_rate=0, in_money_rate=0 → C."""
        data = {"venue_stats": {"東京": {"win_rate": 0, "in_money_rate": 0}}}
        assert _evaluate_course_aptitude(data, "東京") == "C"

    def test_境界値_勝率ちょうど10でB(self):
        """win_rate=10 → B条件成立."""
        data = {"venue_stats": {"東京": {"win_rate": 10, "in_money_rate": 20}}}
        assert _evaluate_course_aptitude(data, "東京") == "B"

    def test_境界値_複勝率ちょうど30でB(self):
        """in_money_rate=30 → B条件成立."""
        data = {"venue_stats": {"東京": {"win_rate": 5, "in_money_rate": 30}}}
        assert _evaluate_course_aptitude(data, "東京") == "B"


# =============================================================================
# _evaluate_jockey テスト
# =============================================================================


class TestEvaluateJockey:
    """騎手評価テスト."""

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_勝率18以上でA評価(self, mock_get):
        """win_rate >= 18.0 → A."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stats": {"win_rate": 20.0}}
        mock_get.return_value = mock_response

        assert _evaluate_jockey("J001") == "A"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_勝率12以上18未満でB評価(self, mock_get):
        """12.0 <= win_rate < 18.0 → B."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stats": {"win_rate": 15.0}}
        mock_get.return_value = mock_response

        assert _evaluate_jockey("J001") == "B"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_勝率8以上12未満でC評価(self, mock_get):
        """8.0 <= win_rate < 12.0 → C."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stats": {"win_rate": 10.0}}
        mock_get.return_value = mock_response

        assert _evaluate_jockey("J001") == "C"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_勝率8未満でC評価(self, mock_get):
        """win_rate < 8.0 → C."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stats": {"win_rate": 5.0}}
        mock_get.return_value = mock_response

        assert _evaluate_jockey("J001") == "C"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_境界値_勝率ちょうど18でA(self, mock_get):
        """win_rate == 18.0 → A."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stats": {"win_rate": 18.0}}
        mock_get.return_value = mock_response

        assert _evaluate_jockey("J001") == "A"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_境界値_勝率ちょうど12でB(self, mock_get):
        """win_rate == 12.0 → B."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stats": {"win_rate": 12.0}}
        mock_get.return_value = mock_response

        assert _evaluate_jockey("J001") == "B"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_境界値_勝率ちょうど8でC(self, mock_get):
        """win_rate == 8.0 → C."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stats": {"win_rate": 8.0}}
        mock_get.return_value = mock_response

        assert _evaluate_jockey("J001") == "C"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_API404でB評価(self, mock_get):
        """API 404 → status_code != 200 → デフォルト B."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        assert _evaluate_jockey("J001") == "B"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_API例外でB評価(self, mock_get):
        """RequestException → デフォルト B."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        assert _evaluate_jockey("J001") == "B"

    @patch("tools.race_comprehensive_analysis.requests.get")
    def test_statsキーなしでC評価(self, mock_get):
        """stats キーがない → {} → win_rate=0.0 → C."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        # win_rate=0.0 < 12.0 → C
        assert _evaluate_jockey("J001") == "C"


# =============================================================================
# _evaluate_body_weight テスト
# =============================================================================


class TestEvaluateBodyWeight:
    """馬体重評価テスト."""

    def test_理想体重帯でA評価(self):
        """460 <= weight <= 500 → A."""
        assert _evaluate_body_weight(480.0) == "A"

    def test_理想体重帯の下限460でA評価(self):
        """weight == 460.0 → A."""
        assert _evaluate_body_weight(460.0) == "A"

    def test_理想体重帯の上限500でA評価(self):
        """weight == 500.0 → A."""
        assert _evaluate_body_weight(500.0) == "A"

    def test_許容範囲内でB評価_軽め(self):
        """440 <= weight < 460 → B."""
        assert _evaluate_body_weight(450.0) == "B"

    def test_許容範囲内でB評価_重め(self):
        """500 < weight <= 520 → B."""
        assert _evaluate_body_weight(510.0) == "B"

    def test_許容範囲の下限440でB評価(self):
        """weight == 440.0 → B."""
        assert _evaluate_body_weight(440.0) == "B"

    def test_許容範囲の上限520でB評価(self):
        """weight == 520.0 → B."""
        assert _evaluate_body_weight(520.0) == "B"

    def test_許容範囲外の軽量でC評価(self):
        """weight < 440 → C."""
        assert _evaluate_body_weight(430.0) == "C"

    def test_許容範囲外の重量でC評価(self):
        """weight > 520 → C."""
        assert _evaluate_body_weight(530.0) == "C"

    def test_極端な軽量でC評価(self):
        """weight = 380 → C."""
        assert _evaluate_body_weight(380.0) == "C"

    def test_極端な重量でC評価(self):
        """weight = 560 → C."""
        assert _evaluate_body_weight(560.0) == "C"


# =============================================================================
# _calculate_overall_score テスト
# =============================================================================


class TestCalculateOverallScore:
    """総合スコア計算テスト."""

    def test_全A評価でスコア上限100(self):
        """全てA → 50 + 25 + 20 + 15 + 10 = 120 → 上限100."""
        factors = {
            "form": "A",
            "course_aptitude": "A",
            "jockey": "A",
            "trainer": "A",
            "weight": "A",
        }
        assert _calculate_overall_score(factors) == 100

    def test_全C評価でスコア16(self):
        """全てC → 50 - 12 - 10 - 7 - 5 = 16（trainerはweightsに含まれず影響なし）."""
        factors = {
            "form": "C",
            "course_aptitude": "C",
            "jockey": "C",
            "trainer": "C",
            "weight": "C",
        }
        assert _calculate_overall_score(factors) == 16

    def test_全B評価でスコアが50になる(self):
        """全てB → ベースの50のまま（B=平均的なので加減点なし）."""
        factors = {
            "form": "B",
            "course_aptitude": "B",
            "jockey": "B",
            "trainer": "B",
            "weight": "B",
        }
        assert _calculate_overall_score(factors) == 50

    def test_formだけA他はC(self):
        """form=A, 他C → 50 + 25 - 10 - 7 - 5 = 53."""
        factors = {
            "form": "A",
            "course_aptitude": "C",
            "jockey": "C",
            "trainer": "C",
            "weight": "C",
        }
        assert _calculate_overall_score(factors) == 53

    def test_course_aptitudeだけA他はC(self):
        """course_aptitude=A, 他C → 50 - 12 + 20 - 7 - 5 = 46."""
        factors = {
            "form": "C",
            "course_aptitude": "A",
            "jockey": "C",
            "trainer": "C",
            "weight": "C",
        }
        assert _calculate_overall_score(factors) == 46

    def test_jockeyだけA他はC(self):
        """jockey=A, 他C → 50 - 12 - 10 + 15 - 5 = 38."""
        factors = {
            "form": "C",
            "course_aptitude": "C",
            "jockey": "A",
            "trainer": "C",
            "weight": "C",
        }
        assert _calculate_overall_score(factors) == 38

    def test_trainerだけA他はC(self):
        """trainer=A, 他C → trainerはweightsに含まれないため無影響 → 50 - 12 - 10 - 7 - 5 = 16."""
        factors = {
            "form": "C",
            "course_aptitude": "C",
            "jockey": "C",
            "trainer": "A",
            "weight": "C",
        }
        assert _calculate_overall_score(factors) == 16

    def test_weightだけA他はC(self):
        """weight=A, 他C → 50 - 12 - 10 - 7 + 10 = 31."""
        factors = {
            "form": "C",
            "course_aptitude": "C",
            "jockey": "C",
            "trainer": "C",
            "weight": "A",
        }
        assert _calculate_overall_score(factors) == 31

    def test_AとBの混在(self):
        """form=A, course_aptitude=B, jockey=A, trainer=C, weight=B → 50 + 25 + 0 + 15 + 0 = 90."""
        factors = {
            "form": "A",
            "course_aptitude": "B",
            "jockey": "A",
            "trainer": "C",
            "weight": "B",
        }
        assert _calculate_overall_score(factors) == 90

    def test_未知のグレードはC扱い(self):
        """factorsに存在しないキーはget(key, 'C')でC扱い → 50 - 12 - 10 - 7 - 5 = 16."""
        factors = {}
        assert _calculate_overall_score(factors) == 16

    def test_不明なグレード文字列はC扱い(self):
        """A/B/C以外の値 → 加算も減点もなし → ベース50のまま."""
        factors = {
            "form": "X",
            "course_aptitude": "X",
            "jockey": "X",
            "trainer": "X",
            "weight": "X",
        }
        assert _calculate_overall_score(factors) == 50


# =============================================================================
# _predict_race_scenario テスト
# =============================================================================


class TestPredictRaceScenario:
    """展開予想テスト."""

    def test_逃げ馬3頭以上でハイペース(self):
        """逃げ馬 >= 3 → ハイペース、差し有利."""
        styles = _make_running_styles([
            (1, "馬1", "逃げ"),
            (2, "馬2", "逃げ"),
            (3, "馬3", "逃げ"),
            (4, "馬4", "先行"),
            (5, "馬5", "差し"),
        ])
        result = _predict_race_scenario(styles)

        assert result["predicted_pace"] == "ハイ"
        assert result["favorable_running_style"] == "差し"
        assert "ハイペース" in result["scenario"]

    def test_逃げ馬0頭でスローペース(self):
        """逃げ馬 = 0 → スローペース、先行有利."""
        styles = _make_running_styles([
            (1, "馬1", "先行"),
            (2, "馬2", "差し"),
            (3, "馬3", "追込"),
        ])
        result = _predict_race_scenario(styles)

        assert result["predicted_pace"] == "スロー"
        assert result["favorable_running_style"] == "先行"
        assert "スローペース" in result["scenario"]

    def test_逃げ馬1頭でスローペース(self):
        """逃げ馬 = 1 → スローペース、先行有利."""
        styles = _make_running_styles([
            (1, "馬1", "逃げ"),
            (2, "馬2", "先行"),
            (3, "馬3", "差し"),
        ])
        result = _predict_race_scenario(styles)

        assert result["predicted_pace"] == "スロー"
        assert result["favorable_running_style"] == "先行"

    def test_逃げ馬2頭でミドルペース(self):
        """逃げ馬 = 2 → ミドルペース."""
        styles = _make_running_styles([
            (1, "馬1", "逃げ"),
            (2, "馬2", "逃げ"),
            (3, "馬3", "先行"),
            (4, "馬4", "差し"),
        ])
        result = _predict_race_scenario(styles)

        assert result["predicted_pace"] == "ミドル"

    def test_ミドルペースで有利脚質が先行と差し(self):
        """ミドルペース時、favorable_running_styleが'先行・差し'になる."""
        styles = _make_running_styles([
            (1, "馬1", "逃げ"),
            (2, "馬2", "逃げ"),
            (3, "馬3", "先行"),
        ])
        result = _predict_race_scenario(styles)

        assert result["predicted_pace"] == "ミドル"
        assert result["favorable_running_style"] == "先行・差し"

    def test_逃げ馬がkey_horseに設定される(self):
        """最初の逃げ馬がkey_horseとして設定される."""
        styles = _make_running_styles([
            (1, "馬1", "先行"),
            (3, "馬3", "逃げ"),
            (5, "馬5", "逃げ"),
        ])
        result = _predict_race_scenario(styles)

        assert result["key_horse"] is not None
        assert result["key_horse"]["number"] == 3
        assert result["key_horse"]["name"] == "馬3"
        assert result["key_horse"]["role"] == "逃げ馬"

    def test_逃げ馬なしでkey_horseはNone(self):
        """逃げ馬がいない → key_horse = None."""
        styles = _make_running_styles([
            (1, "馬1", "先行"),
            (2, "馬2", "差し"),
        ])
        result = _predict_race_scenario(styles)

        assert result["key_horse"] is None

    def test_空リストでスローペース(self):
        """出走馬なし → 逃げ馬0 → スローペース."""
        result = _predict_race_scenario([])

        assert result["predicted_pace"] == "スロー"
        assert result["key_horse"] is None

    def test_不明な脚質はカウントされない(self):
        """'不明'はstyle_countsに含まれない."""
        styles = _make_running_styles([
            (1, "馬1", "不明"),
            (2, "馬2", "不明"),
            (3, "馬3", "逃げ"),
        ])
        result = _predict_race_scenario(styles)

        # 逃げ1頭 → スロー
        assert result["predicted_pace"] == "スロー"


# =============================================================================
# _identify_notable_horses テスト
# =============================================================================


class TestIdentifyNotableHorses:
    """注目馬抽出テスト."""

    def test_本命馬_スコア80以上かつランク3以内(self):
        """score >= 80, rank <= 3 → top_picks."""
        evaluations = [
            _make_runner_evaluation(1, "エース", 90, 1, strengths=["好調", "コース実績"]),
            _make_runner_evaluation(2, "対抗馬", 85, 2, strengths=["騎手◎"]),
            _make_runner_evaluation(3, "三番手", 80, 3),
        ]
        odds_data = {1: 2.0, 2: 5.0, 3: 8.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["top_picks"]) == 3
        assert result["top_picks"][0]["number"] == 1

    def test_本命馬_スコア80未満は対象外(self):
        """score < 80 → top_picksに入らない."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 79, 1),
        ]
        odds_data = {1: 2.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["top_picks"]) == 0

    def test_本命馬_ランク4以下は対象外(self):
        """rank > 3 → top_picksに入らない."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 90, 4),
        ]
        odds_data = {1: 2.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["top_picks"]) == 0

    def test_本命馬は最大3頭まで(self):
        """top_picks[:3] → 最大3頭."""
        evaluations = [
            _make_runner_evaluation(i, f"馬{i}", 90, i) for i in range(1, 5)
        ]
        odds_data = {i: 3.0 for i in range(1, 5)}

        result = _identify_notable_horses(evaluations, odds_data)

        # rank4は対象外なので3頭
        assert len(result["top_picks"]) == 3

    def test_穴馬_スコア65以上でオッズ15倍以上(self):
        """score >= 65, odds >= 15 → value_picks."""
        evaluations = [
            _make_runner_evaluation(5, "穴馬", 70, 5, strengths=["末脚"]),
        ]
        odds_data = {5: 20.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["value_picks"]) == 1
        assert result["value_picks"][0]["number"] == 5
        assert "20.0倍" in result["value_picks"][0]["reason"]
        assert "末脚" in result["value_picks"][0]["reason"]

    def test_穴馬_strengthsが空なら能力上位(self):
        """strengthsなし → '能力上位'が理由に含まれる."""
        evaluations = [
            _make_runner_evaluation(5, "穴馬", 70, 5, strengths=[]),
        ]
        odds_data = {5: 15.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["value_picks"]) == 1
        assert "能力上位" in result["value_picks"][0]["reason"]

    def test_穴馬_スコア65未満は対象外(self):
        """score < 65 → value_picksに入らない."""
        evaluations = [
            _make_runner_evaluation(5, "馬5", 64, 5),
        ]
        odds_data = {5: 20.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["value_picks"]) == 0

    def test_穴馬_オッズ15倍未満は対象外(self):
        """odds < 15 → value_picksに入らない."""
        evaluations = [
            _make_runner_evaluation(5, "馬5", 70, 5),
        ]
        odds_data = {5: 14.9}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["value_picks"]) == 0

    def test_穴馬は最大3頭まで(self):
        """value_picks[:3] → 最大3頭."""
        evaluations = [
            _make_runner_evaluation(i, f"馬{i}", 70, i) for i in range(1, 6)
        ]
        odds_data = {i: 20.0 for i in range(1, 6)}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["value_picks"]) <= 3

    def test_危険人気馬_オッズ5倍以下でスコア65未満(self):
        """odds <= 5.0, score < 65 → danger_favorites."""
        evaluations = [
            _make_runner_evaluation(1, "過剰人気馬", 60, 1, weaknesses=["外枠"]),
        ]
        odds_data = {1: 3.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["danger_favorites"]) == 1
        assert result["danger_favorites"][0]["number"] == 1
        assert "外枠" in result["danger_favorites"][0]["reason"]

    def test_危険人気馬_weaknessesが空なら過剰人気の可能性(self):
        """weaknessesなし → '過剰人気の可能性'が理由に含まれる."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 60, 1, weaknesses=[]),
        ]
        odds_data = {1: 3.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["danger_favorites"]) == 1
        assert "過剰人気の可能性" in result["danger_favorites"][0]["reason"]

    def test_危険人気馬_スコア65以上は対象外(self):
        """score >= 65 → danger_favoritesに入らない."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 65, 1),
        ]
        odds_data = {1: 3.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["danger_favorites"]) == 0

    def test_危険人気馬_オッズ5倍超は対象外(self):
        """odds > 5.0 → danger_favoritesに入らない."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 60, 1),
        ]
        odds_data = {1: 5.1}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["danger_favorites"]) == 0

    def test_危険人気馬_オッズ0は対象外(self):
        """odds = 0 → odds > 0 が False → 対象外."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 60, 1),
        ]
        odds_data = {1: 0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["danger_favorites"]) == 0

    def test_危険人気馬は最大2頭まで(self):
        """danger_favorites[:2] → 最大2頭."""
        evaluations = [
            _make_runner_evaluation(i, f"馬{i}", 60, i) for i in range(1, 5)
        ]
        odds_data = {i: 3.0 for i in range(1, 5)}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["danger_favorites"]) <= 2

    def test_オッズデータなしの馬は穴馬にも危険人気馬にもならない(self):
        """odds_dataに馬番がない → odds=0 → 穴馬/危険人気馬の条件を満たさない."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 90, 1),
        ]
        odds_data = {}

        result = _identify_notable_horses(evaluations, odds_data)

        # top_picksにはなる（オッズ不問）
        assert len(result["top_picks"]) == 1
        assert len(result["value_picks"]) == 0
        assert len(result["danger_favorites"]) == 0

    def test_同じ馬が本命と穴馬を兼ねる(self):
        """score >= 80, rank <= 3, odds >= 15 → top_picksとvalue_picks両方に入る."""
        evaluations = [
            _make_runner_evaluation(1, "二刀流", 85, 1, strengths=["好調"]),
        ]
        odds_data = {1: 20.0}

        result = _identify_notable_horses(evaluations, odds_data)

        assert len(result["top_picks"]) == 1
        assert len(result["value_picks"]) == 1


# =============================================================================
# _generate_betting_suggestion テスト
# =============================================================================


class TestGenerateBettingSuggestion:
    """買い目提案テスト."""

    def test_本命2頭以上で危険人気馬なしなら信頼度高(self):
        """top_picks >= 2, danger_favorites = 0 → 高."""
        notable = {
            "top_picks": [
                {"number": 1, "name": "馬1", "reason": ""},
                {"number": 2, "name": "馬2", "reason": ""},
            ],
            "value_picks": [],
            "danger_favorites": [],
        }
        result = _generate_betting_suggestion(notable)

        assert result["confidence_level"] == "高"
        assert "馬連" in result["suggested_approach"]
        assert result["caution"] == ""

    def test_本命1頭以上と穴馬1頭以上で信頼度中(self):
        """top_picks >= 1, value_picks >= 1 → 中."""
        notable = {
            "top_picks": [{"number": 1, "name": "馬1", "reason": ""}],
            "value_picks": [{"number": 5, "name": "馬5", "reason": ""}],
            "danger_favorites": [],
        }
        result = _generate_betting_suggestion(notable)

        assert result["confidence_level"] == "中"
        assert "ワイド" in result["suggested_approach"]
        assert "3連複" in result["caution"]

    def test_本命2頭以上でも危険人気馬ありなら信頼度中(self):
        """top_picks >= 2だが danger_favorites > 0 → 高の条件を満たさない.
        top_picks >= 1 で value_picks の有無で中 or 低が決まる."""
        notable = {
            "top_picks": [
                {"number": 1, "name": "馬1", "reason": ""},
                {"number": 2, "name": "馬2", "reason": ""},
            ],
            "value_picks": [{"number": 5, "name": "馬5", "reason": ""}],
            "danger_favorites": [{"number": 3, "name": "馬3", "reason": ""}],
        }
        result = _generate_betting_suggestion(notable)

        # 高の条件不成立（danger_favoritesあり）、中の条件成立（top1+value1）
        assert result["confidence_level"] == "中"

    def test_本命なし穴馬なしで信頼度低(self):
        """top_picks = 0, value_picks = 0 → 低."""
        notable = {
            "top_picks": [],
            "value_picks": [],
            "danger_favorites": [],
        }
        result = _generate_betting_suggestion(notable)

        assert result["confidence_level"] == "低"
        assert "ワイド" in result["suggested_approach"]
        assert "混戦" in result["caution"]

    def test_本命1頭のみ穴馬なしで信頼度低(self):
        """top_picks = 1, value_picks = 0 → 中の条件不成立 → 低."""
        notable = {
            "top_picks": [{"number": 1, "name": "馬1", "reason": ""}],
            "value_picks": [],
            "danger_favorites": [],
        }
        result = _generate_betting_suggestion(notable)

        assert result["confidence_level"] == "低"

    def test_空の辞書でも動作する(self):
        """notable_horsesの各キーが空リストでも動作."""
        notable = {
            "top_picks": [],
            "value_picks": [],
            "danger_favorites": [],
        }
        result = _generate_betting_suggestion(notable)

        assert "confidence_level" in result
        assert "suggested_approach" in result
        assert "caution" in result


# =============================================================================
# _evaluate_race_quality テスト
# =============================================================================


class TestEvaluateRaceQuality:
    """レース品質評価テスト."""

    def test_G1はハイレベル(self):
        """grade=G1 → ハイレベル."""
        evaluations = []
        race_info = {"grade": "G1"}
        assert _evaluate_race_quality(evaluations, race_info) == "ハイレベル"

    def test_G2はハイレベル(self):
        """grade=G2 → ハイレベル."""
        evaluations = []
        race_info = {"grade": "G2"}
        assert _evaluate_race_quality(evaluations, race_info) == "ハイレベル"

    def test_G3はグレードだけではハイレベルにならない(self):
        """grade=G3 → グレードでは判定されず、スコア分布で判定."""
        evaluations = [
            _make_runner_evaluation(i, f"馬{i}", 60, i) for i in range(1, 10)
        ]
        race_info = {"grade": "G3"}
        # 65以上が0頭 → 混戦
        assert _evaluate_race_quality(evaluations, race_info) == "混戦"

    def test_高スコア5頭以上でハイレベル(self):
        """score >= 65 が5頭以上 → ハイレベル."""
        evaluations = [
            _make_runner_evaluation(i, f"馬{i}", 70, i) for i in range(1, 6)
        ]
        race_info = {"grade": ""}
        assert _evaluate_race_quality(evaluations, race_info) == "ハイレベル"

    def test_高スコア3頭以上5頭未満で標準(self):
        """3 <= high_score_count < 5 → 標準."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 70, 1),
            _make_runner_evaluation(2, "馬2", 70, 2),
            _make_runner_evaluation(3, "馬3", 65, 3),
            _make_runner_evaluation(4, "馬4", 60, 4),
        ]
        race_info = {"grade": ""}
        assert _evaluate_race_quality(evaluations, race_info) == "標準"

    def test_高スコア3頭未満で混戦(self):
        """high_score_count < 3 → 混戦."""
        evaluations = [
            _make_runner_evaluation(1, "馬1", 70, 1),
            _make_runner_evaluation(2, "馬2", 65, 2),
            _make_runner_evaluation(3, "馬3", 60, 3),
            _make_runner_evaluation(4, "馬4", 50, 4),
        ]
        race_info = {"grade": ""}
        assert _evaluate_race_quality(evaluations, race_info) == "混戦"

    def test_全馬低スコアで混戦(self):
        """全馬 score < 65 → 混戦."""
        evaluations = [
            _make_runner_evaluation(i, f"馬{i}", 50, i) for i in range(1, 10)
        ]
        race_info = {"grade": ""}
        assert _evaluate_race_quality(evaluations, race_info) == "混戦"

    def test_出走馬なしで混戦(self):
        """出走馬0頭 → high_score_count=0 → 混戦."""
        evaluations = []
        race_info = {"grade": ""}
        assert _evaluate_race_quality(evaluations, race_info) == "混戦"

    def test_境界値_スコアちょうど65で高スコア扱い(self):
        """score == 65 → SCORE_GOOD以上 → high_score_countにカウント."""
        evaluations = [
            _make_runner_evaluation(i, f"馬{i}", 65, i) for i in range(1, 6)
        ]
        race_info = {"grade": ""}
        assert _evaluate_race_quality(evaluations, race_info) == "ハイレベル"

    def test_gradeキーなしでも動作(self):
        """race_infoにgradeキーがない → grade='' → スコア分布で判定."""
        evaluations = [
            _make_runner_evaluation(i, f"馬{i}", 70, i) for i in range(1, 4)
        ]
        race_info = {}
        assert _evaluate_race_quality(evaluations, race_info) == "標準"
