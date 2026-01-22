"""買い目分析ツールのテスト."""

import sys
from pathlib import Path

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.bet_analysis import (
    _calculate_expected_value,
    _estimate_win_probability,
    _analyze_weaknesses,
    _calculate_torigami_risk,
    _analyze_bet_selection_impl,
)


class TestEstimateWinProbability:
    """勝率推定のテスト."""

    def test_1番人気の勝率は約33パーセント(self):
        prob = _estimate_win_probability(1)
        assert prob == 0.33

    def test_10番人気の勝率は約2パーセント(self):
        prob = _estimate_win_probability(10)
        assert prob == 0.02

    def test_16番人気の勝率は約0_3パーセント(self):
        prob = _estimate_win_probability(16)
        assert prob == 0.003

    def test_範囲外の人気は最低値を返す(self):
        prob = _estimate_win_probability(20)
        assert prob == 0.002


class TestCalculateExpectedValue:
    """期待値計算のテスト."""

    def test_高オッズ低人気で妙味あり(self):
        # 10番人気（勝率2%）でオッズ100倍 → 期待値 2.0
        result = _calculate_expected_value(100.0, 10)
        assert result["expected_return"] == 2.0
        assert result["value_rating"] == "妙味あり"

    def test_低オッズ高人気で割高(self):
        # 1番人気（勝率33%）でオッズ1.5倍 → 期待値 0.495
        result = _calculate_expected_value(1.5, 1)
        assert result["expected_return"] == 0.49  # 1.5 * 0.33 = 0.495 → round(0.495, 2) = 0.49
        assert result["value_rating"] == "割高"

    def test_適正オッズ(self):
        # 3番人気（勝率13%）でオッズ8倍 → 期待値 1.04
        result = _calculate_expected_value(8.0, 3)
        assert result["expected_return"] == 1.04
        assert result["value_rating"] == "適正"

    def test_オッズ0の場合はデータ不足(self):
        result = _calculate_expected_value(0, 1)
        assert result["value_rating"] == "データ不足"


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
