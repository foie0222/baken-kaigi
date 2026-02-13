"""DynamoDbRaceDataProvider 馬系メソッドのテスト."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.domain.ports.race_data_provider import (
    CourseAptitudeData,
    ExtendedPedigreeData,
    HorsePerformanceData,
    PedigreeData,
    PerformanceData,
    WeightData,
)


def _make_provider():
    """テスト用プロバイダーを作成する."""
    with patch("boto3.resource") as mock_resource:
        from src.infrastructure.providers.dynamodb_race_data_provider import (
            DynamoDbRaceDataProvider,
        )
        provider = DynamoDbRaceDataProvider(region_name="ap-northeast-1")
        return provider, mock_resource


def _runner_item_with_race(**overrides):
    """horse_id-indexからの結果を想定したrunnersアイテム."""
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


class TestGetPastPerformance:

    def test_過去成績を取得する(self):
        provider, mock_resource = _make_provider()

        # runners テーブルの horse_id-index を使うので
        # _runners_table.query を直接モック
        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {
            "Items": [
                _runner_item_with_race(
                    race_id="20260208_06_11",
                    race_date="20260208",
                    finish_position=Decimal("1"),
                    time="1353",
                ),
                _runner_item_with_race(
                    race_id="20260201_05_10",
                    race_date="20260201",
                    finish_position=Decimal("3"),
                    time="1401",
                ),
            ],
        }

        # races テーブルからレース名を取るための参照
        mock_races = MagicMock()
        mock_races.get_item.side_effect = lambda **kw: {
            "Item": {
                "race_name": "テストレース",
                "venue_code": "06",
                "distance": Decimal("1600"),
                "track_condition": "1",
            }
        }
        provider._races_table = mock_races

        result = provider.get_past_performance("2020100001")

        assert len(result) == 2
        assert all(isinstance(r, PerformanceData) for r in result)
        assert result[0].finish_position == 1

    def test_過去成績なしの場合空リストを返す(self):
        provider, mock_resource = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {"Items": []}

        result = provider.get_past_performance("9999999999")
        assert result == []


class TestGetHorsePerformances:

    def test_詳細な過去成績を取得する(self):
        provider, mock_resource = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {
            "Items": [
                _runner_item_with_race(
                    race_id="20260208_06_11",
                    race_date="20260208",
                    finish_position=Decimal("1"),
                    time="1353",
                    last_3f="345",
                ),
            ],
        }

        mock_races = MagicMock()
        mock_races.get_item.return_value = {
            "Item": {
                "race_name": "フェブラリーS",
                "venue_code": "06",
                "distance": Decimal("1600"),
                "track_code": "23",
                "track_condition": "1",
                "horse_count": Decimal("16"),
            }
        }
        provider._races_table = mock_races

        result = provider.get_horse_performances("2020100001", limit=5)

        assert len(result) == 1
        assert isinstance(result[0], HorsePerformanceData)
        assert result[0].race_id == "20260208_06_11"
        assert result[0].finish_position == 1
        assert result[0].venue == "中山"
        assert result[0].track_type == "ダート"

    def test_limit指定で件数を制限する(self):
        provider, mock_resource = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {
            "Items": [
                _runner_item_with_race(race_date=f"202602{i:02d}")
                for i in range(1, 11)
            ],
        }

        mock_races = MagicMock()
        mock_races.get_item.return_value = {
            "Item": {
                "race_name": "テスト",
                "venue_code": "06",
                "distance": Decimal("1600"),
                "track_code": "23",
                "track_condition": "1",
                "horse_count": Decimal("16"),
            }
        }
        provider._races_table = mock_races

        result = provider.get_horse_performances("2020100001", limit=3)
        assert len(result) == 3


class TestGetPedigree:

    def test_血統情報を取得する(self):
        provider, mock_resource = _make_provider()
        provider._horses_table = MagicMock()
        provider._horses_table.get_item.return_value = {
            "Item": {
                "horse_id": "2020100001",
                "sk": "info",
                "horse_name": "テスト馬",
                "sire_name": "テスト父",
                "dam_name": "テスト母",
                "broodmare_sire": "テスト母父",
            }
        }

        result = provider.get_pedigree("2020100001")

        assert result is not None
        assert isinstance(result, PedigreeData)
        assert result.horse_name == "テスト馬"
        assert result.sire_name == "テスト父"
        assert result.dam_name == "テスト母"
        assert result.broodmare_sire == "テスト母父"

    def test_馬が見つからない場合Noneを返す(self):
        provider, mock_resource = _make_provider()
        provider._horses_table = MagicMock()
        provider._horses_table.get_item.return_value = {}

        result = provider.get_pedigree("9999999999")
        assert result is None


class TestGetExtendedPedigree:

    def test_拡張血統情報を取得する(self):
        provider, mock_resource = _make_provider()
        provider._horses_table = MagicMock()
        provider._horses_table.get_item.return_value = {
            "Item": {
                "horse_id": "2020100001",
                "sk": "info",
                "horse_name": "テスト馬",
                "sire_name": "テスト父",
                "dam_name": "テスト母",
                "broodmare_sire": "テスト母父",
            }
        }

        result = provider.get_extended_pedigree("2020100001")

        assert result is not None
        assert isinstance(result, ExtendedPedigreeData)
        assert result.horse_name == "テスト馬"
        assert result.sire is not None
        assert result.sire.name == "テスト父"
        assert result.dam is not None
        assert result.dam.name == "テスト母"

    def test_馬が見つからない場合Noneを返す(self):
        provider, mock_resource = _make_provider()
        provider._horses_table = MagicMock()
        provider._horses_table.get_item.return_value = {}

        result = provider.get_extended_pedigree("9999999999")
        assert result is None


class TestGetWeightHistory:

    def test_体重履歴を取得する(self):
        provider, mock_resource = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {
            "Items": [
                _runner_item_with_race(
                    race_date="20260208",
                    weight=Decimal("480"),
                    weight_diff=Decimal("-2"),
                ),
                _runner_item_with_race(
                    race_date="20260201",
                    weight=Decimal("482"),
                    weight_diff=Decimal("4"),
                ),
            ],
        }

        result = provider.get_weight_history("2020100001", limit=5)

        assert len(result) == 2
        assert all(isinstance(w, WeightData) for w in result)
        assert result[0].weight == 480
        assert result[1].weight == 482

    def test_体重データなしの場合空リストを返す(self):
        provider, mock_resource = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {
            "Items": [
                _runner_item_with_race(),  # weight フィールドなし
            ],
        }

        result = provider.get_weight_history("2020100001")
        assert result == []


class TestGetCourseAptitude:

    def test_コース適性データを取得する(self):
        provider, mock_resource = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {
            "Items": [
                _runner_item_with_race(
                    race_id="20260208_06_11",
                    race_date="20260208",
                    finish_position=Decimal("1"),
                ),
                _runner_item_with_race(
                    race_id="20260201_06_10",
                    race_date="20260201",
                    finish_position=Decimal("3"),
                ),
                _runner_item_with_race(
                    race_id="20260125_05_05",
                    race_date="20260125",
                    finish_position=Decimal("2"),
                ),
            ],
        }

        mock_races = MagicMock()
        mock_races.get_item.side_effect = lambda **kw: {
            "Item": {
                "race_name": "テスト",
                "venue_code": kw["Key"]["race_id"].split("_")[1],
                "distance": Decimal("1600"),
                "track_code": "23",
                "track_condition": "1",
                "horse_count": Decimal("16"),
            }
        }
        provider._races_table = mock_races

        provider._horses_table = MagicMock()
        provider._horses_table.get_item.return_value = {
            "Item": {"horse_name": "テスト馬"},
        }

        result = provider.get_course_aptitude("2020100001")

        assert result is not None
        assert isinstance(result, CourseAptitudeData)
        assert result.horse_id == "2020100001"
        # 2回中山、1回東京なので会場別データがある
        assert len(result.by_venue) >= 1

    def test_成績なしの場合Noneを返す(self):
        provider, mock_resource = _make_provider()
        provider._runners_table = MagicMock()
        provider._runners_table.query.return_value = {"Items": []}

        result = provider.get_course_aptitude("9999999999")
        assert result is None


class TestStubMethods:

    def test_get_horse_trainingは空データを返す(self):
        provider, _ = _make_provider()
        records, summary = provider.get_horse_training("2020100001")
        assert records == []
        assert summary is None

    def test_get_jra_checksumはNoneを返す(self):
        provider, _ = _make_provider()
        result = provider.get_jra_checksum("06", "01", 1, 11)
        assert result is None
