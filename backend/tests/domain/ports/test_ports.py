"""ポート（RaceDataProvider）のテスト."""
from abc import ABC

from src.domain.ports import (
    JockeyStatsData,
    RaceData,
    RaceDataProvider,
    RunnerData,
)


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
