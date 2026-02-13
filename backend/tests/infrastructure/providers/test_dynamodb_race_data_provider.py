"""DynamoDbRaceDataProvider のテスト（基本6メソッド）."""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.domain.identifiers import RaceId
from src.domain.ports.race_data_provider import (
    RaceData,
    RaceResultData,
    RaceResultsData,
    RunnerData,
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


def _race_item(**overrides):
    """レーステーブルのテスト用アイテムを作成する."""
    item = {
        "race_date": "20260215",
        "race_id": "20260215_06_11",
        "race_number": Decimal("11"),
        "race_name": "フェブラリーS",
        "venue_code": "06",
        "track_code": "23",
        "distance": Decimal("1600"),
        "track_condition": "1",
        "horse_count": Decimal("16"),
        "grade_code": "1",
        "condition_code": "A3",
        "start_time": "1540",
    }
    item.update(overrides)
    return item


def _runner_item(**overrides):
    """runnersテーブルのテスト用アイテムを作成する."""
    item = {
        "race_id": "20260215_06_11",
        "race_date": "20260215",
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
        "finish_position": Decimal("0"),
        "time": "",
        "last_3f": "",
    }
    item.update(overrides)
    return item


class TestGetRace:

    def test_正常系_レースIDで検索して結果を返す(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {
            "Items": [_race_item()],
        }

        result = provider.get_race(RaceId("20260215_06_11"))

        assert result is not None
        assert isinstance(result, RaceData)
        assert result.race_id == "20260215_06_11"
        assert result.race_name == "フェブラリーS"
        assert result.distance == 1600
        assert result.horse_count == 16
        assert result.venue == "中山"
        assert result.track_type == "ダート"

    def test_存在しないレースIDの場合Noneを返す(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {"Items": []}

        result = provider.get_race(RaceId("99991231_99_99"))
        assert result is None


class TestGetRacesByDate:

    def test_日付でレース一覧を取得する(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {
            "Items": [
                _race_item(race_id="20260215_06_01", race_number=Decimal("1"),
                           race_name="1R"),
                _race_item(race_id="20260215_06_11", race_number=Decimal("11")),
            ],
        }

        result = provider.get_races_by_date(date(2026, 2, 15))

        assert len(result) == 2
        assert all(isinstance(r, RaceData) for r in result)
        # レース番号順にソート
        assert result[0].race_number == 1
        assert result[1].race_number == 11

    def test_開催場指定でフィルタする(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {
            "Items": [
                _race_item(venue_code="06"),
                _race_item(
                    race_id="20260215_05_01", venue_code="05",
                    race_name="東京1R", race_number=Decimal("1"),
                ),
            ],
        }

        result = provider.get_races_by_date(date(2026, 2, 15), venue="中山")

        assert len(result) == 1
        assert result[0].venue == "中山"

    def test_レースなしの場合空リストを返す(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {"Items": []}

        result = provider.get_races_by_date(date(2026, 2, 15))
        assert result == []


class TestGetRunners:

    def test_正常系_出走馬一覧を取得する(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {
            "Items": [
                _runner_item(horse_number=Decimal("1"), horse_name="馬1"),
                _runner_item(horse_number=Decimal("3"), horse_name="馬3"),
            ],
        }

        result = provider.get_runners(RaceId("20260215_06_11"))

        assert len(result) == 2
        assert all(isinstance(r, RunnerData) for r in result)
        assert result[0].horse_number == 1
        assert result[1].horse_number == 3

    def test_出走馬なしの場合空リストを返す(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {"Items": []}

        result = provider.get_runners(RaceId("20260215_06_11"))
        assert result == []


class TestGetRaceWeights:

    def test_馬体重データがない場合は空辞書を返す(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {
            "Items": [
                _runner_item(horse_number=Decimal("3")),
            ],
        }

        result = provider.get_race_weights(RaceId("20260215_06_11"))
        assert result == {}

    def test_馬体重データがある場合はWeightDataを返す(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.query.return_value = {
            "Items": [
                _runner_item(
                    horse_number=Decimal("3"),
                    weight=Decimal("480"),
                    weight_diff=Decimal("-2"),
                ),
                _runner_item(
                    horse_number=Decimal("5"),
                    weight=Decimal("500"),
                    weight_diff=Decimal("4"),
                ),
            ],
        }

        result = provider.get_race_weights(RaceId("20260215_06_11"))
        assert len(result) == 2
        assert result[3].weight == 480
        assert result[3].weight_diff == -2
        assert result[5].weight == 500
        assert result[5].weight_diff == 4


class TestGetRaceDates:

    def test_開催日一覧を返す(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.scan.return_value = {
            "Items": [
                {"race_date": "20260215"},
                {"race_date": "20260215"},
                {"race_date": "20260208"},
                {"race_date": "20260222"},
            ],
        }

        result = provider.get_race_dates()

        # 重複排除＆降順
        assert len(result) == 3
        assert result[0] == date(2026, 2, 22)
        assert result[1] == date(2026, 2, 15)
        assert result[2] == date(2026, 2, 8)

    def test_日付範囲指定でフィルタする(self):
        provider, mock_resource = _make_provider()
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.scan.return_value = {
            "Items": [
                {"race_date": "20260201"},
                {"race_date": "20260208"},
                {"race_date": "20260215"},
                {"race_date": "20260222"},
            ],
        }

        result = provider.get_race_dates(
            from_date=date(2026, 2, 5),
            to_date=date(2026, 2, 20),
        )

        assert len(result) == 2
        assert result[0] == date(2026, 2, 15)
        assert result[1] == date(2026, 2, 8)


class TestGetRaceResults:

    def test_確定済みレース結果を返す(self):
        provider, mock_resource = _make_provider()

        # races テーブルと runners テーブルで異なるモックが必要
        mock_races_table = MagicMock()
        mock_runners_table = MagicMock()

        def table_router(name):
            if "races" in name:
                return mock_races_table
            return mock_runners_table

        mock_resource.return_value.Table.side_effect = table_router

        mock_races_table.query.return_value = {
            "Items": [_race_item()],
        }
        mock_runners_table.query.return_value = {
            "Items": [
                _runner_item(
                    horse_number=Decimal("3"),
                    horse_name="テスト馬1",
                    finish_position=Decimal("1"),
                    time="1353",
                    last_3f="345",
                    popularity=Decimal("2"),
                    odds="5.6",
                ),
                _runner_item(
                    horse_number=Decimal("5"),
                    horse_name="テスト馬2",
                    finish_position=Decimal("2"),
                    time="1355",
                    last_3f="348",
                    popularity=Decimal("5"),
                    odds="12.3",
                ),
            ],
        }

        # プロバイダーを再構築（table routerを使うため）
        from src.infrastructure.providers.dynamodb_race_data_provider import (
            DynamoDbRaceDataProvider,
        )
        provider = DynamoDbRaceDataProvider.__new__(DynamoDbRaceDataProvider)
        provider._races_table = mock_races_table
        provider._runners_table = mock_runners_table

        result = provider.get_race_results(RaceId("20260215_06_11"))

        assert result is not None
        assert isinstance(result, RaceResultsData)
        assert result.race_id == "20260215_06_11"
        assert result.is_finalized is True
        assert len(result.results) == 2
        assert result.results[0].finish_position == 1
        assert result.results[0].horse_name == "テスト馬1"
        assert result.results[1].finish_position == 2

    def test_未確定の場合Noneを返す(self):
        provider, mock_resource = _make_provider()

        mock_races_table = MagicMock()
        mock_runners_table = MagicMock()

        def table_router(name):
            if "races" in name:
                return mock_races_table
            return mock_runners_table

        mock_resource.return_value.Table.side_effect = table_router

        mock_races_table.query.return_value = {"Items": [_race_item()]}
        mock_runners_table.query.return_value = {
            "Items": [
                _runner_item(finish_position=Decimal("0")),
            ],
        }

        from src.infrastructure.providers.dynamodb_race_data_provider import (
            DynamoDbRaceDataProvider,
        )
        provider = DynamoDbRaceDataProvider.__new__(DynamoDbRaceDataProvider)
        provider._races_table = mock_races_table
        provider._runners_table = mock_runners_table

        result = provider.get_race_results(RaceId("20260215_06_11"))
        assert result is None
