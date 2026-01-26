"""種牡馬APIハンドラーのテスト."""
import json
from datetime import date

import pytest

from src.api.dependencies import Dependencies
from src.domain.identifiers import RaceId
from src.domain.ports import (
    CourseAptitudeData,
    ExtendedPedigreeData,
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
    """テスト用のモックレースデータプロバイダ."""

    def __init__(self) -> None:
        self._stallion_stats: dict[str, tuple] = {}

    def add_stallion_stats(
        self,
        stallion_id: str,
        stats: StallionOffspringStatsData,
        track_stats: list[StallionTrackStatsData],
        distance_stats: list[StallionDistanceStatsData],
        condition_stats: list[StallionConditionStatsData],
        top_offspring: list[TopOffspringData],
    ) -> None:
        """テスト用に種牡馬成績を追加."""
        self._stallion_stats[stallion_id] = (
            stats,
            track_stats,
            distance_stats,
            condition_stats,
            top_offspring,
        )

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
        """過去の同条件レース統計を取得する（モック実装）."""
        return None

    def get_jockey_info(self, jockey_id: str) -> JockeyInfoData | None:
        """騎手基本情報を取得する（モック実装）."""
        return None

    def get_jockey_stats_detail(
        self,
        jockey_id: str,
        year: int | None = None,
        period: str = "recent",
    ) -> JockeyStatsDetailData | None:
        """騎手成績統計を取得する（モック実装）."""
        return None

    def get_horse_performances(
        self,
        horse_id: str,
        limit: int = 5,
        track_type: str | None = None,
    ) -> list[HorsePerformanceData]:
        """馬の過去成績を取得する（モック実装）."""
        return []

    def get_horse_training(
        self,
        horse_id: str,
        limit: int = 5,
        days: int = 30,
    ) -> tuple[list[TrainingRecordData], TrainingSummaryData | None]:
        """馬の調教データを取得する（モック実装）."""
        return [], None

    def get_extended_pedigree(self, horse_id: str) -> ExtendedPedigreeData | None:
        """馬の拡張血統情報を取得する（モック実装）."""
        return None

    def get_odds_history(self, race_id: RaceId) -> OddsHistoryData | None:
        """レースのオッズ履歴を取得する（モック実装）."""
        return None

    def get_course_aptitude(self, horse_id: str) -> CourseAptitudeData | None:
        """馬のコース適性を取得する（モック実装）."""
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
        """種牡馬産駒成績を取得する（モック実装）."""
        if stallion_id in self._stallion_stats:
            return self._stallion_stats[stallion_id]
        return None, [], [], [], []

    def get_trainer_info(self, trainer_id: str) -> TrainerInfoData | None:
        """厩舎基本情報を取得する（モック実装）."""
        return None

    def get_trainer_stats_detail(
        self,
        trainer_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> tuple[TrainerStatsDetailData | None, list[TrainerTrackStatsData], list[TrainerClassStatsData]]:
        """厩舎成績統計を取得する（モック実装）."""
        return None, [], []


@pytest.fixture(autouse=True)
def reset_dependencies():
    """各テスト前に依存性をリセット."""
    Dependencies.reset()
    yield
    Dependencies.reset()


class TestGetStallionOffspringStatsHandler:
    """GET /stallions/{stallion_id}/offspring-stats ハンドラーのテスト."""

    def test_種牡馬産駒成績を取得できる(self) -> None:
        """種牡馬産駒成績を取得できることを確認."""
        from src.api.handlers.stallions import get_stallion_offspring_stats

        provider = MockRaceDataProvider()
        stats = StallionOffspringStatsData(
            stallion_id="stallion1",
            stallion_name="ディープインパクト",
            total_offspring=500,
            total_starts=3000,
            wins=600,
            win_rate=20.0,
            place_rate=50.0,
            g1_wins=50,
            earnings=1000000000,
        )
        track_stats = [
            StallionTrackStatsData(
                track_type="芝",
                starts=2000,
                wins=450,
                win_rate=22.5,
                avg_distance=1800,
            ),
            StallionTrackStatsData(
                track_type="ダート",
                starts=1000,
                wins=150,
                win_rate=15.0,
                avg_distance=1600,
            ),
        ]
        distance_stats = [
            StallionDistanceStatsData(
                distance_range="1600m以下",
                starts=800,
                wins=180,
                win_rate=22.5,
            ),
        ]
        condition_stats = [
            StallionConditionStatsData(
                condition="良",
                starts=2500,
                wins=520,
                win_rate=20.8,
            ),
        ]
        top_offspring = [
            TopOffspringData(
                horse_name="コントレイル",
                wins=10,
                g1_wins=4,
            ),
        ]
        provider.add_stallion_stats(
            "stallion1", stats, track_stats, distance_stats, condition_stats, top_offspring
        )
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"stallion_id": "stallion1"}}

        response = get_stallion_offspring_stats(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["stallion_id"] == "stallion1"
        assert body["stallion_name"] == "ディープインパクト"
        assert body["total_offspring"] == 500
        assert body["stats"]["wins"] == 600
        assert body["stats"]["g1_wins"] == 50
        assert len(body["by_track_type"]) == 2
        assert len(body["by_distance"]) == 1
        assert len(body["by_track_condition"]) == 1
        assert len(body["top_offspring"]) == 1
        assert body["top_offspring"][0]["horse_name"] == "コントレイル"

    def test_存在しない種牡馬で404(self) -> None:
        """存在しない種牡馬で404が返ることを確認."""
        from src.api.handlers.stallions import get_stallion_offspring_stats

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {"stallion_id": "nonexistent"}}

        response = get_stallion_offspring_stats(event, None)

        assert response["statusCode"] == 404

    def test_stallion_idがない場合400(self) -> None:
        """stallion_idがない場合400が返ることを確認."""
        from src.api.handlers.stallions import get_stallion_offspring_stats

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {"pathParameters": {}}

        response = get_stallion_offspring_stats(event, None)

        assert response["statusCode"] == 400

    def test_yearパラメータでフィルタできる(self) -> None:
        """yearパラメータでフィルタできることを確認."""
        from src.api.handlers.stallions import get_stallion_offspring_stats

        provider = MockRaceDataProvider()
        stats = StallionOffspringStatsData(
            stallion_id="stallion1",
            stallion_name="ディープインパクト",
            total_offspring=100,
            total_starts=500,
            wins=100,
            win_rate=20.0,
            place_rate=50.0,
            g1_wins=10,
        )
        provider.add_stallion_stats("stallion1", stats, [], [], [], [])
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"stallion_id": "stallion1"},
            "queryStringParameters": {"year": "2024"},
        }

        response = get_stallion_offspring_stats(event, None)

        assert response["statusCode"] == 200

    def test_不正なyearパラメータで400(self) -> None:
        """不正なyearパラメータで400が返ることを確認."""
        from src.api.handlers.stallions import get_stallion_offspring_stats

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"stallion_id": "stallion1"},
            "queryStringParameters": {"year": "invalid"},
        }

        response = get_stallion_offspring_stats(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "year" in body["error"]["message"]

    def test_範囲外のyearパラメータで400(self) -> None:
        """範囲外のyearパラメータで400が返ることを確認."""
        from src.api.handlers.stallions import get_stallion_offspring_stats

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"stallion_id": "stallion1"},
            "queryStringParameters": {"year": "1900"},
        }

        response = get_stallion_offspring_stats(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "1970" in body["error"]["message"]

    def test_track_typeパラメータでフィルタできる(self) -> None:
        """track_typeパラメータでフィルタできることを確認."""
        from src.api.handlers.stallions import get_stallion_offspring_stats

        provider = MockRaceDataProvider()
        stats = StallionOffspringStatsData(
            stallion_id="stallion1",
            stallion_name="ディープインパクト",
            total_offspring=100,
            total_starts=500,
            wins=100,
            win_rate=20.0,
            place_rate=50.0,
            g1_wins=10,
        )
        provider.add_stallion_stats("stallion1", stats, [], [], [], [])
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"stallion_id": "stallion1"},
            "queryStringParameters": {"track_type": "芝"},
        }

        response = get_stallion_offspring_stats(event, None)

        assert response["statusCode"] == 200

    def test_不正なtrack_typeパラメータで400(self) -> None:
        """不正なtrack_typeパラメータで400が返ることを確認."""
        from src.api.handlers.stallions import get_stallion_offspring_stats

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"stallion_id": "stallion1"},
            "queryStringParameters": {"track_type": "砂"},
        }

        response = get_stallion_offspring_stats(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "track_type" in body["error"]["message"]
