"""レース総合分析ツールの騎手/調教師/馬体重評価ロジックのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))
    from tools.race_comprehensive_analysis import (
        _evaluate_jockey,
        _evaluate_trainer,
        _evaluate_weight_change,
        _evaluate_horse_factors,
        _calculate_overall_score,
    )
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_jravan_client():
    """JRA-VANクライアントをモック化."""
    with patch("tools.race_comprehensive_analysis.get_api_url", return_value="https://api.example.com"):
        yield


# =============================================================================
# 騎手評価 (_evaluate_jockey) テスト
# =============================================================================


class TestEvaluateJockey:
    """騎手評価テスト."""

    def test_騎手評価_勝率18以上でA(self):
        """勝率18%以上 → A（リーディング上位クラス）."""
        jockey_stats = {"win_rate": 20.0, "place_rate": 50.0}
        assert _evaluate_jockey(jockey_stats) == "A"

    def test_騎手評価_勝率ちょうど18でA(self):
        """勝率ちょうど18% → A."""
        jockey_stats = {"win_rate": 18.0, "place_rate": 40.0}
        assert _evaluate_jockey(jockey_stats) == "A"

    def test_騎手評価_勝率12以上18未満でB(self):
        """勝率12%以上18%未満 → B（平均的）."""
        jockey_stats = {"win_rate": 15.0, "place_rate": 35.0}
        assert _evaluate_jockey(jockey_stats) == "B"

    def test_騎手評価_勝率ちょうど12でB(self):
        """勝率ちょうど12% → B."""
        jockey_stats = {"win_rate": 12.0, "place_rate": 30.0}
        assert _evaluate_jockey(jockey_stats) == "B"

    def test_騎手評価_勝率8以上12未満でC(self):
        """勝率8%以上12%未満 → C（やや低い）."""
        jockey_stats = {"win_rate": 10.0, "place_rate": 25.0}
        assert _evaluate_jockey(jockey_stats) == "C"

    def test_騎手評価_勝率ちょうど8でC(self):
        """勝率ちょうど8% → C."""
        jockey_stats = {"win_rate": 8.0, "place_rate": 20.0}
        assert _evaluate_jockey(jockey_stats) == "C"

    def test_騎手評価_勝率8未満でD(self):
        """勝率8%未満 → D（新人/低勝率）."""
        jockey_stats = {"win_rate": 5.0, "place_rate": 15.0}
        assert _evaluate_jockey(jockey_stats) == "D"

    def test_騎手評価_勝率0でD(self):
        """勝率0% → D."""
        jockey_stats = {"win_rate": 0.0, "place_rate": 0.0}
        assert _evaluate_jockey(jockey_stats) == "D"

    def test_騎手評価_statsが空辞書ならB(self):
        """騎手データなし → デフォルトB."""
        assert _evaluate_jockey({}) == "B"

    def test_騎手評価_win_rateキーなしならB(self):
        """win_rateキーがない → デフォルトB."""
        jockey_stats = {"place_rate": 40.0}
        assert _evaluate_jockey(jockey_stats) == "B"

    def test_騎手評価_statsネスト構造でも正しく評価(self):
        """{"stats": {"win_rate": 20.0}} 形式にも対応."""
        jockey_stats = {"stats": {"win_rate": 20.0, "place_rate": 50.0}}
        assert _evaluate_jockey(jockey_stats) == "A"

    def test_騎手評価_statsネスト構造でwin_rateなしならB(self):
        """{"stats": {}} 形式 → デフォルトB."""
        jockey_stats = {"stats": {"place_rate": 40.0}}
        assert _evaluate_jockey(jockey_stats) == "B"


# =============================================================================
# 調教師評価 (_evaluate_trainer) テスト
# =============================================================================


class TestEvaluateTrainer:
    """調教師評価テスト."""

    def test_調教師評価_勝率15以上でA(self):
        """勝率15%以上 → A（有力厩舎）."""
        trainer_stats = {"win_rate": 18.0, "place_rate": 50.0}
        assert _evaluate_trainer(trainer_stats) == "A"

    def test_調教師評価_勝率ちょうど15でA(self):
        """勝率ちょうど15% → A."""
        trainer_stats = {"win_rate": 15.0, "place_rate": 45.0}
        assert _evaluate_trainer(trainer_stats) == "A"

    def test_調教師評価_勝率10以上15未満でB(self):
        """勝率10%以上15%未満 → B（平均的）."""
        trainer_stats = {"win_rate": 12.0, "place_rate": 35.0}
        assert _evaluate_trainer(trainer_stats) == "B"

    def test_調教師評価_勝率ちょうど10でB(self):
        """勝率ちょうど10% → B."""
        trainer_stats = {"win_rate": 10.0, "place_rate": 30.0}
        assert _evaluate_trainer(trainer_stats) == "B"

    def test_調教師評価_勝率10未満でC(self):
        """勝率10%未満 → C."""
        trainer_stats = {"win_rate": 7.0, "place_rate": 20.0}
        assert _evaluate_trainer(trainer_stats) == "C"

    def test_調教師評価_勝率0でC(self):
        """勝率0% → C."""
        trainer_stats = {"win_rate": 0.0, "place_rate": 0.0}
        assert _evaluate_trainer(trainer_stats) == "C"

    def test_調教師評価_statsが空辞書ならB(self):
        """調教師データなし → デフォルトB."""
        assert _evaluate_trainer({}) == "B"

    def test_調教師評価_win_rateキーなしならB(self):
        """win_rateキーがない → デフォルトB."""
        trainer_stats = {"place_rate": 40.0}
        assert _evaluate_trainer(trainer_stats) == "B"

    def test_調教師評価_statsネスト構造でも正しく評価(self):
        """{"stats": {"win_rate": 18.0}} 形式にも対応."""
        trainer_stats = {"stats": {"win_rate": 18.0, "place_rate": 50.0}}
        assert _evaluate_trainer(trainer_stats) == "A"

    def test_調教師評価_statsネスト構造でwin_rateなしならB(self):
        """{"stats": {}} 形式 → デフォルトB."""
        trainer_stats = {"stats": {"place_rate": 40.0}}
        assert _evaluate_trainer(trainer_stats) == "B"


# =============================================================================
# 馬体重変動評価 (_evaluate_weight_change) テスト
# =============================================================================


class TestEvaluateWeightChange:
    """馬体重変動評価テスト."""

    def test_体重変動_増減0はA(self):
        """前走比0kg → A（適正範囲内）."""
        assert _evaluate_weight_change(0) == "A"

    def test_体重変動_プラス2はA(self):
        """前走比+2kg → A（適正範囲内）."""
        assert _evaluate_weight_change(2) == "A"

    def test_体重変動_マイナス2はA(self):
        """前走比-2kg → A."""
        assert _evaluate_weight_change(-2) == "A"

    def test_体重変動_プラス4はA(self):
        """前走比+4kg → A（4kg以内は適正）."""
        assert _evaluate_weight_change(4) == "A"

    def test_体重変動_マイナス4はA(self):
        """前走比-4kg → A."""
        assert _evaluate_weight_change(-4) == "A"

    def test_体重変動_プラス6はB(self):
        """前走比+6kg → B（やや変動）."""
        assert _evaluate_weight_change(6) == "B"

    def test_体重変動_マイナス6はB(self):
        """前走比-6kg → B."""
        assert _evaluate_weight_change(-6) == "B"

    def test_体重変動_プラス8はB(self):
        """前走比+8kg → B（5-9kgはやや変動）."""
        assert _evaluate_weight_change(8) == "B"

    def test_体重変動_プラス10はC(self):
        """前走比+10kg → C（大幅増減）."""
        assert _evaluate_weight_change(10) == "C"

    def test_体重変動_マイナス10はC(self):
        """前走比-10kg → C."""
        assert _evaluate_weight_change(-10) == "C"

    def test_体重変動_プラス14はC(self):
        """前走比+14kg → C（10-14kgは大幅変動）."""
        assert _evaluate_weight_change(14) == "C"

    def test_体重変動_プラス16はD(self):
        """前走比+16kg → D（異常な変動）."""
        assert _evaluate_weight_change(16) == "D"

    def test_体重変動_マイナス16はD(self):
        """前走比-16kg → D."""
        assert _evaluate_weight_change(-16) == "D"

    def test_体重変動_NoneはB(self):
        """体重変動データなし → デフォルトB."""
        assert _evaluate_weight_change(None) == "B"


# =============================================================================
# _evaluate_horse_factors のjockey/trainer/weight統合テスト
# =============================================================================


class TestEvaluateHorseFactorsWithNewFields:
    """_evaluate_horse_factorsの騎手/調教師/馬体重評価統合テスト."""

    @patch("tools.race_comprehensive_analysis.cached_get")
    def test_騎手と調教師のstatsがAPIから取得される(self, mock_get):
        """rider情報がrunnerデータから引き継がれ、APIで詳細を取得する."""
        from unittest.mock import MagicMock

        # 各APIエンドポイントの応答を設定
        def side_effect(url, **kwargs):
            response = MagicMock()
            response.status_code = 200
            if "/performances" in url:
                response.json.return_value = {"performances": []}
            elif "/course-aptitude" in url:
                response.json.return_value = {"venue_stats": {}}
            elif "/jockeys/" in url and "/stats" in url:
                response.json.return_value = {"win_rate": 20.0, "place_rate": 50.0}
            elif "/trainers/" in url and "/stats" in url:
                response.json.return_value = {"win_rate": 16.0, "place_rate": 45.0}
            return response

        mock_get.side_effect = side_effect

        runner = {
            "horse_id": "horse_001",
            "jockey_id": "jockey_001",
            "trainer_id": "trainer_001",
            "weight_diff": 2,
        }
        race_info = {"venue": "東京"}

        factors = _evaluate_horse_factors(runner, race_info)

        assert factors["jockey"] == "A"  # 勝率20% → A
        assert factors["trainer"] == "A"  # 勝率16% → A
        assert factors["weight"] == "A"  # +2kg → A

    @patch("tools.race_comprehensive_analysis.cached_get")
    def test_騎手APIが404の場合デフォルトB(self, mock_get):
        """騎手APIが404を返す場合、デフォルトのBになる."""
        from unittest.mock import MagicMock

        def side_effect(url, **kwargs):
            response = MagicMock()
            if "/jockeys/" in url:
                response.status_code = 404
            elif "/trainers/" in url:
                response.status_code = 404
            else:
                response.status_code = 200
                if "/performances" in url:
                    response.json.return_value = {"performances": []}
                elif "/course-aptitude" in url:
                    response.json.return_value = {"venue_stats": {}}
            return response

        mock_get.side_effect = side_effect

        runner = {
            "horse_id": "horse_001",
            "jockey_id": "jockey_001",
            "trainer_id": "trainer_001",
            "weight_diff": None,
        }
        race_info = {"venue": "東京"}

        factors = _evaluate_horse_factors(runner, race_info)

        assert factors["jockey"] == "B"
        assert factors["trainer"] == "B"
        assert factors["weight"] == "B"

    @patch("tools.race_comprehensive_analysis.cached_get")
    def test_runner情報にjockey_idがない場合デフォルトB(self, mock_get):
        """runnerにjockey_idがない場合、騎手評価はデフォルトB."""
        from unittest.mock import MagicMock

        def side_effect(url, **kwargs):
            response = MagicMock()
            response.status_code = 200
            if "/performances" in url:
                response.json.return_value = {"performances": []}
            elif "/course-aptitude" in url:
                response.json.return_value = {"venue_stats": {}}
            return response

        mock_get.side_effect = side_effect

        runner = {"horse_id": "horse_001"}
        race_info = {"venue": "東京"}

        factors = _evaluate_horse_factors(runner, race_info)

        assert factors["jockey"] == "B"
        assert factors["trainer"] == "B"
        assert factors["weight"] == "B"


# =============================================================================
# _calculate_overall_score のjockey/trainer/weight反映テスト
# =============================================================================


class TestCalculateOverallScoreWithNewWeights:
    """jockey/trainer/weightがスコアに反映されるテスト."""

    def test_全A評価で最大スコア(self):
        """全要素A → 50 + 25 + 20 + 15 + 10 + 10 = 130 → 100（上限）."""
        factors = {
            "form": "A",
            "course_aptitude": "A",
            "jockey": "A",
            "trainer": "A",
            "weight": "A",
        }
        assert _calculate_overall_score(factors) == 100

    def test_全C評価で最小スコア(self):
        """全要素C → 50 - 12 - 10 - 7 - 5 - 5 = 11."""
        factors = {
            "form": "C",
            "course_aptitude": "C",
            "jockey": "C",
            "trainer": "C",
            "weight": "C",
        }
        assert _calculate_overall_score(factors) == 11

    def test_全B評価で50(self):
        """全要素B → ベース50のまま."""
        factors = {
            "form": "B",
            "course_aptitude": "B",
            "jockey": "B",
            "trainer": "B",
            "weight": "B",
        }
        assert _calculate_overall_score(factors) == 50

    def test_jockeyだけA他はB(self):
        """jockey=A → 50 + 15 = 65."""
        factors = {
            "form": "B",
            "course_aptitude": "B",
            "jockey": "A",
            "trainer": "B",
            "weight": "B",
        }
        assert _calculate_overall_score(factors) == 65

    def test_trainerだけA他はB(self):
        """trainer=A → 50 + 10 = 60."""
        factors = {
            "form": "B",
            "course_aptitude": "B",
            "jockey": "B",
            "trainer": "A",
            "weight": "B",
        }
        assert _calculate_overall_score(factors) == 60

    def test_weightだけA他はB(self):
        """weight=A → 50 + 10 = 60."""
        factors = {
            "form": "B",
            "course_aptitude": "B",
            "jockey": "B",
            "trainer": "B",
            "weight": "A",
        }
        assert _calculate_overall_score(factors) == 60

    def test_D評価はC評価と同じ減点(self):
        """D評価の場合もCと同じ減点（weight // 2）."""
        factors_c = {
            "form": "B",
            "course_aptitude": "B",
            "jockey": "C",
            "trainer": "B",
            "weight": "B",
        }
        factors_d = {
            "form": "B",
            "course_aptitude": "B",
            "jockey": "D",
            "trainer": "B",
            "weight": "B",
        }
        assert _calculate_overall_score(factors_c) == _calculate_overall_score(factors_d)

    def test_formとjockeyがA他はC(self):
        """form=A, jockey=A → 50 + 25 + 15 - 10 - 5 - 5 = 70."""
        factors = {
            "form": "A",
            "course_aptitude": "C",
            "jockey": "A",
            "trainer": "C",
            "weight": "C",
        }
        assert _calculate_overall_score(factors) == 70

    def test_スコアの下限は0(self):
        """大幅な減点でも0を下回らない."""
        factors = {}  # 全キーなし → 全てCデフォルト
        score = _calculate_overall_score(factors)
        assert score >= 0

    def test_スコアの上限は100(self):
        """大幅な加点でも100を超えない."""
        factors = {
            "form": "A",
            "course_aptitude": "A",
            "jockey": "A",
            "trainer": "A",
            "weight": "A",
        }
        score = _calculate_overall_score(factors)
        assert score <= 100
