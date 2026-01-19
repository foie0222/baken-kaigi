"""ポート（AIClient, RaceDataProvider）のテスト."""
from abc import ABC

from src.domain.ports import AIClient, AmountFeedbackContext, BetFeedbackContext, ConsultationContext
from src.domain.ports import (
    JockeyStatsData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
)


class TestAIClient:
    """AIClientの単体テスト."""

    def test_AIClientは抽象基底クラスである(self) -> None:
        """AIClientがABCを継承していることを確認."""
        assert issubclass(AIClient, ABC)

    def test_BetFeedbackContextを生成できる(self) -> None:
        """BetFeedbackContextを生成できることを確認."""
        context = BetFeedbackContext(
            race_name="日本ダービー",
            horse_numbers=[1, 2, 3],
            horse_names=["馬A", "馬B", "馬C"],
            recent_results=["1-1-1", "2-2-2", "3-3-3"],
            jockey_stats=["勝率20%", "勝率30%", "勝率10%"],
            track_suitability=["良馬場得意", "重馬場得意", "万能"],
            current_odds=["2.5", "5.0", "10.0"],
        )
        assert context.race_name == "日本ダービー"

    def test_AmountFeedbackContextを生成できる(self) -> None:
        """AmountFeedbackContextを生成できることを確認."""
        context = AmountFeedbackContext(
            total_amount=5000,
            remaining_loss_limit=10000,
            average_amount=3000,
            is_limit_exceeded=False,
        )
        assert context.total_amount == 5000

    def test_ConsultationContextを生成できる(self) -> None:
        """ConsultationContextを生成できることを確認."""
        context = ConsultationContext(
            cart_summary="単勝5番 1000円",
            data_feedback_summary="好調な馬です",
            amount_feedback_summary="限度額内です",
        )
        assert context.cart_summary == "単勝5番 1000円"


class TestRaceDataProvider:
    """RaceDataProviderの単体テスト."""

    def test_RaceDataProviderは抽象基底クラスである(self) -> None:
        """RaceDataProviderがABCを継承していることを確認."""
        assert issubclass(RaceDataProvider, ABC)

    def test_RaceDataを生成できる(self) -> None:
        """RaceDataを生成できることを確認."""
        from datetime import datetime
        data = RaceData(
            race_id="2024010101",
            race_name="日本ダービー",
            race_number=11,
            venue="東京",
            start_time=datetime(2024, 5, 26, 15, 40),
            betting_deadline=datetime(2024, 5, 26, 15, 30),
            track_condition="良",
        )
        assert data.race_name == "日本ダービー"

    def test_RunnerDataを生成できる(self) -> None:
        """RunnerDataを生成できることを確認."""
        data = RunnerData(
            horse_number=5,
            horse_name="ディープインパクト",
            horse_id="horse-001",
            jockey_name="武豊",
            jockey_id="jockey-001",
            odds="2.5",
            popularity=1,
        )
        assert data.horse_name == "ディープインパクト"

    def test_PerformanceDataを生成できる(self) -> None:
        """PerformanceDataを生成できることを確認."""
        from datetime import datetime
        data = PerformanceData(
            race_date=datetime(2024, 4, 1),
            race_name="皐月賞",
            venue="中山",
            finish_position=1,
            distance=2000,
            track_condition="良",
            time="1:59.5",
        )
        assert data.finish_position == 1

    def test_JockeyStatsDataを生成できる(self) -> None:
        """JockeyStatsDataを生成できることを確認."""
        data = JockeyStatsData(
            jockey_id="jockey-001",
            jockey_name="武豊",
            course="東京芝2400m",
            total_races=100,
            wins=25,
            win_rate=0.25,
            place_rate=0.50,
        )
        assert data.wins == 25
