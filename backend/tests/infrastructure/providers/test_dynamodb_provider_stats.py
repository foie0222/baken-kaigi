"""DynamoDbRaceDataProvider 人物・統計系メソッドのテスト."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.domain.ports.race_data_provider import (
    GatePositionStatsData,
    JockeyInfoData,
    JockeyStatsData,
    JockeyStatsDetailData,
    PastRaceStats,
    TrainerInfoData,
    TrainerStatsDetailData,
)


def _make_provider():
    """テスト用プロバイダーを作成する."""
    with patch("boto3.resource") as mock_resource:
        from src.infrastructure.providers.dynamodb_race_data_provider import (
            DynamoDbRaceDataProvider,
        )
        provider = DynamoDbRaceDataProvider(region_name="ap-northeast-1")
        return provider, mock_resource


def _runner_item(**overrides):
    """runnersテーブルのテスト用アイテム."""
    item = {
        "race_id": "20260208_06_11",
        "race_date": "20260208",
        "horse_number": Decimal("3"),
        "horse_name": "テスト馬",
        "horse_id": "2020100001",
        "jockey_id": "01234",
        "jockey_name": "テスト騎手",
        "trainer_id": "05678",
        "odds": "5.6",
        "popularity": Decimal("2"),
        "waku_ban": Decimal("2"),
        "weight_carried": "57.0",
        "finish_position": Decimal("1"),
        "time": "1353",
        "last_3f": "345",
    }
    item.update(overrides)
    return item


class TestGetJockeyStats:

    def test_騎手のコース成績を返す(self):
        provider, _ = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.scan.return_value = {
            "Items": [
                _runner_item(jockey_id="01234", finish_position=Decimal("1")),
                _runner_item(jockey_id="01234", finish_position=Decimal("2")),
                _runner_item(jockey_id="01234", finish_position=Decimal("5")),
            ],
        }

        provider._races_table = MagicMock()
        provider._races_table.get_item.return_value = {
            "Item": {"venue_code": "06", "track_code": "23",
                     "distance": Decimal("1600"), "track_condition": "1",
                     "horse_count": Decimal("16")},
        }

        provider._jockeys_table = MagicMock()
        provider._jockeys_table.get_item.return_value = {
            "Item": {"jockey_name": "テスト騎手"},
        }

        result = provider.get_jockey_stats("01234", "中山")

        assert result is not None
        assert isinstance(result, JockeyStatsData)
        assert result.jockey_id == "01234"
        assert result.total_races == 3
        assert result.wins == 1

    def test_成績なしの場合Noneを返す(self):
        provider, _ = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.scan.return_value = {"Items": []}

        result = provider.get_jockey_stats("99999", "中山")
        assert result is None


class TestGetJockeyInfo:

    def test_騎手基本情報を返す(self):
        provider, _ = _make_provider()
        provider._jockeys_table = MagicMock()
        provider._jockeys_table.get_item.return_value = {
            "Item": {
                "jockey_id": "01234",
                "jockey_name": "テスト騎手",
                "jockey_name_kana": "テストキシュ",
                "affiliation": "美浦",
            },
        }

        result = provider.get_jockey_info("01234")

        assert result is not None
        assert isinstance(result, JockeyInfoData)
        assert result.jockey_name == "テスト騎手"
        assert result.affiliation == "美浦"

    def test_見つからない場合Noneを返す(self):
        provider, _ = _make_provider()
        provider._jockeys_table = MagicMock()
        provider._jockeys_table.get_item.return_value = {}

        result = provider.get_jockey_info("99999")
        assert result is None


class TestGetJockeyStatsDetail:

    def test_騎手成績統計を返す(self):
        provider, _ = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.scan.return_value = {
            "Items": [
                _runner_item(jockey_id="01234", finish_position=Decimal("1")),
                _runner_item(jockey_id="01234", finish_position=Decimal("2")),
                _runner_item(jockey_id="01234", finish_position=Decimal("3")),
                _runner_item(jockey_id="01234", finish_position=Decimal("5")),
            ],
        }

        provider._jockeys_table = MagicMock()
        provider._jockeys_table.get_item.return_value = {
            "Item": {"jockey_name": "テスト騎手"},
        }

        result = provider.get_jockey_stats_detail("01234")

        assert result is not None
        assert isinstance(result, JockeyStatsDetailData)
        assert result.total_rides == 4
        assert result.wins == 1
        assert result.second_places == 1
        assert result.third_places == 1


class TestGetTrainerInfo:

    def test_調教師基本情報を返す(self):
        provider, _ = _make_provider()
        provider._trainers_table = MagicMock()
        provider._trainers_table.get_item.return_value = {
            "Item": {
                "trainer_id": "05678",
                "trainer_name": "テスト調教師",
                "trainer_name_kana": "テストチョウキョウシ",
                "affiliation": "栗東",
            },
        }

        result = provider.get_trainer_info("05678")

        assert result is not None
        assert isinstance(result, TrainerInfoData)
        assert result.trainer_name == "テスト調教師"
        assert result.affiliation == "栗東"

    def test_見つからない場合Noneを返す(self):
        provider, _ = _make_provider()
        provider._trainers_table = MagicMock()
        provider._trainers_table.get_item.return_value = {}

        result = provider.get_trainer_info("99999")
        assert result is None


class TestGetTrainerStatsDetail:

    def test_調教師成績統計を返す(self):
        provider, _ = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.scan.return_value = {
            "Items": [
                _runner_item(trainer_id="05678", finish_position=Decimal("1")),
                _runner_item(trainer_id="05678", finish_position=Decimal("4")),
            ],
        }

        provider._trainers_table = MagicMock()
        provider._trainers_table.get_item.return_value = {
            "Item": {"trainer_name": "テスト調教師"},
        }

        provider._races_table = MagicMock()
        provider._races_table.get_item.return_value = {
            "Item": {"track_code": "23", "grade_code": "1"},
        }

        stats, track_stats, class_stats = provider.get_trainer_stats_detail("05678")

        assert stats is not None
        assert isinstance(stats, TrainerStatsDetailData)
        assert stats.total_starts == 2
        assert stats.wins == 1


class TestGetPastRaceStats:

    def test_過去レース統計を返す(self):
        provider, _ = _make_provider()
        provider._runners_table = MagicMock()
        provider._races_table = MagicMock()

        # races テーブル scan で条件に合うレースを検索
        provider._races_table.scan.return_value = {
            "Items": [
                {"race_id": "20260208_06_11", "race_date": "20260208",
                 "track_code": "23", "distance": Decimal("1600"),
                 "grade_code": "1", "horse_count": Decimal("16"),
                 "venue_code": "06"},
            ],
        }

        # 該当レースの runners を取得
        provider._runners_table.query.return_value = {
            "Items": [
                _runner_item(finish_position=Decimal("1"), popularity=Decimal("1")),
                _runner_item(finish_position=Decimal("2"), popularity=Decimal("3"),
                             horse_number=Decimal("5")),
            ],
        }

        result = provider.get_past_race_stats("ダート", 1600)

        assert result is not None
        assert isinstance(result, PastRaceStats)
        assert result.total_races == 1
        assert result.track_type == "ダート"
        assert result.distance == 1600


class TestGetGatePositionStats:

    def test_枠順別成績統計を返す(self):
        provider, _ = _make_provider()
        provider._races_table = MagicMock()
        provider._races_table.scan.return_value = {
            "Items": [
                {"race_id": "20260208_06_11", "race_date": "20260208",
                 "venue_code": "06", "track_code": "23",
                 "distance": Decimal("1600"), "track_condition": "1",
                 "horse_count": Decimal("16")},
            ],
        }

        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {
            "Items": [
                _runner_item(waku_ban=Decimal("1"), finish_position=Decimal("1"),
                             horse_number=Decimal("1")),
                _runner_item(waku_ban=Decimal("8"), finish_position=Decimal("5"),
                             horse_number=Decimal("16")),
            ],
        }

        result = provider.get_gate_position_stats("中山")

        assert result is not None
        assert isinstance(result, GatePositionStatsData)
        assert result.total_races == 1
        assert len(result.by_gate) >= 1


class TestStubStatsMethodsReturnDefaults:

    def test_get_odds_historyはNoneを返す(self):
        from src.domain.identifiers import RaceId
        provider, _ = _make_provider()
        result = provider.get_odds_history(RaceId("20260208_06_11"))
        assert result is None

    def test_get_stallion_offspring_statsはデフォルトを返す(self):
        provider, _ = _make_provider()
        result = provider.get_stallion_offspring_stats("2020100001")
        assert result == (None, [], [], [], [])

    def test_get_owner_infoはNoneを返す(self):
        provider, _ = _make_provider()
        assert provider.get_owner_info("O001") is None

    def test_get_owner_statsはNoneを返す(self):
        provider, _ = _make_provider()
        assert provider.get_owner_stats("O001") is None

    def test_get_breeder_infoはNoneを返す(self):
        provider, _ = _make_provider()
        assert provider.get_breeder_info("B001") is None

    def test_get_breeder_statsはNoneを返す(self):
        provider, _ = _make_provider()
        assert provider.get_breeder_stats("B001") is None
