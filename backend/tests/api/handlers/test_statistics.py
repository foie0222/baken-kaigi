"""統計APIハンドラーのテスト."""
import json
from datetime import date

import pytest

from src.api.dependencies import Dependencies
from src.api.handlers.statistics import get_gate_position_stats
from src.domain.identifiers import RaceId
from src.domain.ports import (
    CourseAptitudeData,
    ExtendedPedigreeData,
    GateAnalysisData,
    GatePositionConditionsData,
    GatePositionStatsData,
    GateStatsData,
    HorseNumberStatsData,
    HorsePerformanceData,
    JockeyInfoData,
    JockeyStatsData,
    JockeyStatsDetailData,
    OddsHistoryData,
    PastRaceStats,
    PedigreeData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
    StallionConditionStatsData,
    StallionDistanceStatsData,
    StallionOffspringStatsData,
    StallionTrackStatsData,
    TopOffspringData,
    TrainerClassStatsData,
    TrainerInfoData,
    TrainerStatsDetailData,
    TrainerTrackStatsData,
    TrainingRecordData,
    TrainingSummaryData,
    WeightData,
)


class MockRaceDataProvider(RaceDataProvider):
    """テスト用のモック実装."""

    def __init__(self) -> None:
        self._gate_position_stats: dict[str, GatePositionStatsData] = {}

    def add_gate_position_stats(self, key: str, stats: GatePositionStatsData) -> None:
        """テスト用に枠順統計を追加."""
        self._gate_position_stats[key] = stats

    def get_race(self, race_id: RaceId) -> RaceData | None:
        return None

    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        return []

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        return []

    def get_past_performance(self, horse_id: str) -> list[PerformanceData]:
        return []

    def get_jockey_stats(self, jockey_id: str, course: str) -> JockeyStatsData | None:
        return None

    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        return None

    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        return []

    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        return {}

    def get_jra_checksum(
        self,
        venue_code: str,
        kaisai_kai: str,
        kaisai_nichime: int,
        race_number: int,
    ) -> int | None:
        return None

    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        return []

    def get_past_race_stats(
        self,
        track_type: str,
        distance: int,
        grade_class: str | None = None,
        limit: int = 100
    ) -> PastRaceStats | None:
        return None

    def get_jockey_info(self, jockey_id: str) -> JockeyInfoData | None:
        return None

    def get_jockey_stats_detail(
        self,
        jockey_id: str,
        year: int | None = None,
        period: str = "recent",
    ) -> JockeyStatsDetailData | None:
        return None

    def get_horse_performances(
        self,
        horse_id: str,
        limit: int = 5,
        track_type: str | None = None,
    ) -> list[HorsePerformanceData]:
        return []

    def get_horse_training(
        self,
        horse_id: str,
        limit: int = 5,
        days: int = 30,
    ) -> tuple[list[TrainingRecordData], TrainingSummaryData | None]:
        return [], None

    def get_extended_pedigree(self, horse_id: str) -> ExtendedPedigreeData | None:
        return None

    def get_odds_history(self, race_id: RaceId) -> OddsHistoryData | None:
        return None

    def get_course_aptitude(self, horse_id: str) -> CourseAptitudeData | None:
        return None

    def get_stallion_offspring_stats(
        self,
        stallion_id: str,
        year: int | None = None,
        track_type: str | None = None,
    ) -> tuple[
        StallionOffspringStatsData | None,
        list[StallionTrackStatsData],
        list[StallionDistanceStatsData],
        list[StallionConditionStatsData],
        list[TopOffspringData],
    ]:
        return None, [], [], [], []

    def get_trainer_info(self, trainer_id: str) -> TrainerInfoData | None:
        return None

    def get_trainer_stats_detail(
        self,
        trainer_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> tuple[TrainerStatsDetailData | None, list[TrainerTrackStatsData], list[TrainerClassStatsData]]:
        return None, [], []

    def get_gate_position_stats(
        self,
        venue: str,
        track_type: str | None = None,
        distance: int | None = None,
        track_condition: str | None = None,
        limit: int = 100,
    ) -> GatePositionStatsData | None:
        """枠順別成績統計を取得する（モック実装）."""
        key = f"{venue}_{track_type}_{distance}_{track_condition}"
        return self._gate_position_stats.get(key)


@pytest.fixture(autouse=True)
def reset_dependencies():
    """各テスト前に依存性をリセット."""
    Dependencies.reset()
    yield
    Dependencies.reset()


class TestGetGatePositionStats:
    """GET /statistics/gate-position ハンドラーのテスト."""

    def test_必須パラメータvenueがない場合は400エラー(self) -> None:
        """venueパラメータがない場合は400を返す."""
        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"queryStringParameters": {}}
        result = get_gate_position_stats(event, {})

        assert result["statusCode"] == 400
        assert "venue is required" in result["body"]

    def test_存在しない競馬場の場合は404エラー(self) -> None:
        """存在しない競馬場の場合は404を返す."""
        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"queryStringParameters": {"venue": "nonexistent"}}
        result = get_gate_position_stats(event, {})

        assert result["statusCode"] == 404

    def test_無効なdistanceは400エラー(self) -> None:
        """無効なdistanceパラメータは400を返す."""
        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"queryStringParameters": {"venue": "阪神", "distance": "invalid"}}
        result = get_gate_position_stats(event, {})

        assert result["statusCode"] == 400
        assert "Invalid distance format" in result["body"]

    def test_limit範囲外は400エラー(self) -> None:
        """limit範囲外の場合は400を返す."""
        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"queryStringParameters": {"venue": "阪神", "limit": "1000"}}
        result = get_gate_position_stats(event, {})

        assert result["statusCode"] == 400
        assert "limit must be between 1 and 500" in result["body"]

    def test_正常に枠順統計を取得できる(self) -> None:
        """正常に枠順統計を取得できることを確認."""
        provider = MockRaceDataProvider()

        # ダミーの統計データを作成
        conditions = GatePositionConditionsData(
            venue="阪神",
            track_type="芝",
            distance=1600,
            track_condition=None,
        )
        by_gate = [
            GateStatsData(
                gate=1,
                gate_range="1-2枠",
                starts=100,
                wins=20,
                places=40,
                win_rate=20.0,
                place_rate=40.0,
                avg_finish=5.2,
            )
        ]
        by_horse_number = [
            HorseNumberStatsData(
                horse_number=1,
                starts=50,
                wins=10,
                win_rate=20.0,
            )
        ]
        analysis = GateAnalysisData(
            favorable_gates=[1, 2],
            unfavorable_gates=[7, 8],
            comment="阪神芝1600mは内枠有利",
        )
        stats = GatePositionStatsData(
            conditions=conditions,
            total_races=100,
            by_gate=by_gate,
            by_horse_number=by_horse_number,
            analysis=analysis,
        )
        provider.add_gate_position_stats("阪神_芝_1600_None", stats)
        Dependencies.set_race_data_provider(provider)

        event = {"queryStringParameters": {"venue": "阪神", "track_type": "芝", "distance": "1600"}}
        result = get_gate_position_stats(event, {})

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["conditions"]["venue"] == "阪神"
        assert body["conditions"]["track_type"] == "芝"
        assert body["conditions"]["distance"] == 1600
        assert body["total_races"] == 100
        assert len(body["by_gate"]) == 1
        assert body["by_gate"][0]["gate"] == 1
        assert body["by_gate"][0]["win_rate"] == 20.0
        assert len(body["by_horse_number"]) == 1
        assert body["analysis"]["favorable_gates"] == [1, 2]
        assert body["analysis"]["comment"] == "阪神芝1600mは内枠有利"
