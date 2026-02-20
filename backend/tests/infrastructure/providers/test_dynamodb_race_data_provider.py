"""DynamoDbRaceDataProviderのテスト."""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from src.domain.identifiers import RaceId
from src.domain.ports import RaceData, RunnerData
from src.infrastructure.providers.dynamodb_race_data_provider import (
    DynamoDbRaceDataProvider,
)

JST = timezone(timedelta(hours=9))


def _make_race_item() -> dict:
    """テスト用レースアイテムを生成する."""
    return {
        "race_date": "20260214",
        "race_id": "202602140505",
        "venue": "東京",
        "venue_code": "05",
        "race_number": Decimal("5"),
        "race_name": "サンプルレース",
        "grade": "05",
        "distance": Decimal("1600"),
        "track_type": "芝",
        "track_code": "10",
        "horse_count": Decimal("16"),
        "post_time": "1425",
        "turf_condition_code": "1",
        "dirt_condition_code": "2",
        "kaisai_kai": "01",
        "kaisai_nichime": "02",
    }


def _make_runner_item(*, horse_number: str = "05") -> dict:
    """テスト用出走馬アイテムを生成する."""
    return {
        "race_id": "202602140505",
        "horse_number": horse_number,
        "horse_id": "2020100001",
        "horse_name": "サンプルホース",
        "waku_ban": Decimal("3"),
        "jockey_id": "01234",
        "jockey_name": "川田将雅",
        "odds": Decimal("5.4"),
        "popularity": Decimal("2"),
    }


class TestGetRace:
    """get_raceメソッドのテスト."""

    def test_正常にレース情報を取得できる(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": _make_race_item()}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_race(RaceId("202602140505"))

        assert result is not None
        assert isinstance(result, RaceData)
        assert result.race_id == "202602140505"
        assert result.race_name == "サンプルレース"
        assert result.race_number == 5
        assert result.venue == "05"
        assert result.start_time == datetime(2026, 2, 14, 14, 25, tzinfo=JST)
        assert result.betting_deadline == result.start_time
        assert result.track_condition == "良"
        assert result.track_type == "芝"
        assert result.distance == 1600
        assert result.horse_count == 16
        assert result.grade_class == "05"
        assert result.is_obstacle is False
        assert result.kaisai_kai == "01"
        assert result.kaisai_nichime == "02"
        assert result.age_condition == ""

        mock_table.get_item.assert_called_once_with(
            Key={"race_date": "20260214", "race_id": "202602140505"}
        )

    def test_存在しないレースはNoneを返す(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_race(RaceId("202602149999"))

        assert result is None

    def test_post_timeが空の場合ダミー時刻を使用する(self):
        item = _make_race_item()
        item["post_time"] = ""

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": item}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_race(RaceId("202602140505"))

        assert result is not None
        assert result.start_time.tzinfo == JST

    def test_ダートの馬場状態はdirt_condition_codeを使う(self):
        item = _make_race_item()
        item["track_type"] = "ダート"
        item["turf_condition_code"] = "1"
        item["dirt_condition_code"] = "3"

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": item}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_race(RaceId("202602140505"))

        assert result is not None
        assert result.track_condition == "重"

    def test_障害レースはis_obstacleがTrueになる(self):
        item = _make_race_item()
        item["track_type"] = "障害"

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": item}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_race(RaceId("202602140505"))

        assert result is not None
        assert result.is_obstacle is True

    def test_不明なcondition_codeは空文字を返す(self):
        item = _make_race_item()
        item["turf_condition_code"] = "9"

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": item}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_race(RaceId("202602140505"))

        assert result is not None
        assert result.track_condition == ""


class TestGetRunners:
    """get_runnersメソッドのテスト."""

    def test_正常に出走馬リストを取得できる(self):
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                _make_runner_item(horse_number="03"),
                _make_runner_item(horse_number="01"),
                _make_runner_item(horse_number="05"),
            ]
        }

        provider = DynamoDbRaceDataProvider(
            races_table=MagicMock(), runners_table=mock_table
        )
        result = provider.get_runners(RaceId("202602140505"))

        assert len(result) == 3
        assert all(isinstance(r, RunnerData) for r in result)
        # horse_number順にソートされている
        assert result[0].horse_number == 1
        assert result[1].horse_number == 3
        assert result[2].horse_number == 5

    def test_出走馬データの変換が正しい(self):
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [_make_runner_item()]
        }

        provider = DynamoDbRaceDataProvider(
            races_table=MagicMock(), runners_table=mock_table
        )
        result = provider.get_runners(RaceId("202602140505"))

        assert len(result) == 1
        runner = result[0]
        assert runner.horse_number == 5
        assert runner.horse_name == "サンプルホース"
        assert runner.horse_id == "2020100001"
        assert runner.jockey_name == "川田将雅"
        assert runner.jockey_id == "01234"
        assert runner.odds == "5.4"
        assert runner.popularity == 2
        assert runner.waku_ban == 3

    def test_出走馬が存在しない場合は空リストを返す(self):
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}

        provider = DynamoDbRaceDataProvider(
            races_table=MagicMock(), runners_table=mock_table
        )
        result = provider.get_runners(RaceId("202602149999"))

        assert result == []

    def test_horse_number順にソートされる(self):
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                _make_runner_item(horse_number="16"),
                _make_runner_item(horse_number="02"),
                _make_runner_item(horse_number="08"),
                _make_runner_item(horse_number="01"),
            ]
        }

        provider = DynamoDbRaceDataProvider(
            races_table=MagicMock(), runners_table=mock_table
        )
        result = provider.get_runners(RaceId("202602140505"))

        numbers = [r.horse_number for r in result]
        assert numbers == [1, 2, 8, 16]


class TestGetRacesByDate:
    """get_races_by_dateメソッドのテスト."""

    def test_正常にレース一覧を取得できる(self):
        mock_table = MagicMock()
        item1 = _make_race_item()
        item1["venue"] = "東京"
        item1["venue_code"] = "05"
        item1["race_number"] = Decimal("1")
        item2 = _make_race_item()
        item2["venue"] = "中山"
        item2["venue_code"] = "06"
        item2["race_number"] = Decimal("3")
        item2["race_id"] = "202602140303"
        mock_table.query.return_value = {"Items": [item2, item1]}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_races_by_date(date(2026, 2, 14))

        assert len(result) == 2
        assert all(isinstance(r, RaceData) for r in result)
        # venue_code順 → race_number順
        assert result[0].venue == "05"
        assert result[1].venue == "06"

    def test_venueフィルタで絞り込める(self):
        mock_table = MagicMock()
        item_tokyo = _make_race_item()
        item_tokyo["venue"] = "東京"
        item_tokyo["venue_code"] = "05"
        item_nakayama = _make_race_item()
        item_nakayama["venue"] = "中山"
        item_nakayama["venue_code"] = "06"
        item_nakayama["race_id"] = "202602140303"
        mock_table.query.return_value = {"Items": [item_tokyo, item_nakayama]}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_races_by_date(date(2026, 2, 14), venue="05")

        assert len(result) == 1
        assert result[0].venue == "05"

    def test_該当レースがない場合は空リストを返す(self):
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_races_by_date(date(2026, 3, 1))

        assert result == []

    def test_同一会場内でrace_number順にソートされる(self):
        mock_table = MagicMock()
        item1 = _make_race_item()
        item1["venue"] = "東京"
        item1["race_number"] = Decimal("11")
        item1["race_id"] = "202602140511"
        item2 = _make_race_item()
        item2["venue"] = "東京"
        item2["race_number"] = Decimal("3")
        item2["race_id"] = "202602140503"
        item3 = _make_race_item()
        item3["venue"] = "東京"
        item3["race_number"] = Decimal("7")
        item3["race_id"] = "202602140507"
        mock_table.query.return_value = {"Items": [item1, item2, item3]}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_races_by_date(date(2026, 2, 14))

        race_numbers = [r.race_number for r in result]
        assert race_numbers == [3, 7, 11]


class TestConstructor:
    """コンストラクタのテスト."""

    def test_テーブル直接注入(self):
        mock_races = MagicMock()
        mock_runners = MagicMock()

        provider = DynamoDbRaceDataProvider(
            races_table=mock_races, runners_table=mock_runners
        )

        assert provider._races_table is mock_races
        assert provider._runners_table is mock_runners


class TestUnsupportedMethods:
    """DynamoDB未対応メソッドのテスト."""

    def _make_provider(self) -> DynamoDbRaceDataProvider:
        return DynamoDbRaceDataProvider(
            races_table=MagicMock(), runners_table=MagicMock()
        )

    def test_get_jockey_statsはNoneを返す(self):
        result = self._make_provider().get_jockey_stats("01234", "東京芝1600")
        assert result is None

    def test_get_pedigreeはNoneを返す(self):
        result = self._make_provider().get_pedigree("2020100001")
        assert result is None

    def test_get_weight_historyは空リストを返す(self):
        result = self._make_provider().get_weight_history("2020100001")
        assert result == []

    def test_get_race_weightsは空辞書を返す(self):
        result = self._make_provider().get_race_weights(RaceId("202602140505"))
        assert result == {}

    def test_get_jra_checksumはNoneを返す(self):
        result = self._make_provider().get_jra_checksum("05", "01", 2, 5)
        assert result is None

    def test_get_past_race_statsはNoneを返す(self):
        result = self._make_provider().get_past_race_stats("芝", 1600)
        assert result is None

    def test_get_jockey_infoはNoneを返す(self):
        result = self._make_provider().get_jockey_info("01234")
        assert result is None

    def test_get_jockey_stats_detailはNoneを返す(self):
        result = self._make_provider().get_jockey_stats_detail("01234")
        assert result is None

    def test_get_horse_performancesは空リストを返す(self):
        result = self._make_provider().get_horse_performances("2020100001")
        assert result == []

    def test_get_horse_trainingは空リストとNoneのタプルを返す(self):
        records, summary = self._make_provider().get_horse_training("2020100001")
        assert records == []
        assert summary is None

    def test_get_extended_pedigreeはNoneを返す(self):
        result = self._make_provider().get_extended_pedigree("2020100001")
        assert result is None

    def test_get_odds_historyはNoneを返す(self):
        result = self._make_provider().get_odds_history(RaceId("202602140505"))
        assert result is None

    def test_get_running_stylesは空リストを返す(self):
        result = self._make_provider().get_running_styles(RaceId("202602140505"))
        assert result == []

    def test_get_course_aptitudeはNoneを返す(self):
        result = self._make_provider().get_course_aptitude("2020100001")
        assert result is None

    def test_get_trainer_infoはNoneを返す(self):
        result = self._make_provider().get_trainer_info("01234")
        assert result is None

    def test_get_trainer_stats_detailはNoneと空リストのタプルを返す(self):
        result = self._make_provider().get_trainer_stats_detail("01234")
        assert result == (None, [], [])

    def test_get_stallion_offspring_statsはNoneと空リストのタプルを返す(self):
        result = self._make_provider().get_stallion_offspring_stats("2020100001")
        assert result == (None, [], [], [], [])

    def test_get_gate_position_statsはNoneを返す(self):
        result = self._make_provider().get_gate_position_stats("東京")
        assert result is None

    def test_get_race_resultsはNoneを返す(self):
        result = self._make_provider().get_race_results(RaceId("202602140505"))
        assert result is None

    def test_get_owner_infoはNoneを返す(self):
        result = self._make_provider().get_owner_info("00001")
        assert result is None

    def test_get_owner_statsはNoneを返す(self):
        result = self._make_provider().get_owner_stats("00001")
        assert result is None

    def test_get_breeder_infoはNoneを返す(self):
        result = self._make_provider().get_breeder_info("00001")
        assert result is None

    def test_get_breeder_statsはNoneを返す(self):
        result = self._make_provider().get_breeder_stats("00001")
        assert result is None

    def test_get_all_oddsはNoneを返す(self):
        result = self._make_provider().get_all_odds(RaceId("202602140505"))
        assert result is None


class TestGetRaceDates:
    """get_race_datesメソッドのテスト."""

    def _make_provider(self, scan_items: list[dict]) -> DynamoDbRaceDataProvider:
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": scan_items}
        return DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )

    def test_期間内の開催日をdate型のソート済みリストで返す(self):
        provider = self._make_provider([
            {"race_date": "20260215"},
            {"race_date": "20260214"},
            {"race_date": "20260215"},  # 重複
            {"race_date": "20260221"},
        ])

        result = provider.get_race_dates(
            from_date=date(2026, 2, 7), to_date=date(2026, 3, 7)
        )

        assert result == [date(2026, 2, 21), date(2026, 2, 15), date(2026, 2, 14)]

    def test_引数なしで全件スキャンする(self):
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [{"race_date": "20260214"}, {"race_date": "20260221"}]
        }
        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )

        result = provider.get_race_dates()

        assert result == [date(2026, 2, 21), date(2026, 2, 14)]
        call_kwargs = mock_table.scan.call_args[1]
        assert "FilterExpression" not in call_kwargs

    def test_from_dateのみ指定でフィルタする(self):
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": [{"race_date": "20260221"}]}
        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )

        result = provider.get_race_dates(from_date=date(2026, 2, 15))

        assert result == [date(2026, 2, 21)]
        call_kwargs = mock_table.scan.call_args[1]
        assert "FilterExpression" in call_kwargs

    def test_to_dateのみ指定でフィルタする(self):
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": [{"race_date": "20260214"}]}
        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )

        result = provider.get_race_dates(to_date=date(2026, 2, 28))

        assert result == [date(2026, 2, 14)]
        call_kwargs = mock_table.scan.call_args[1]
        assert "FilterExpression" in call_kwargs

    def test_レースがない場合は空リストを返す(self):
        provider = self._make_provider([])

        result = provider.get_race_dates(
            from_date=date(2026, 3, 1), to_date=date(2026, 3, 31)
        )

        assert result == []

    def test_ページネーションを正しく処理する(self):
        mock_table = MagicMock()
        mock_table.scan.side_effect = [
            {
                "Items": [{"race_date": "20260214"}],
                "LastEvaluatedKey": {"race_date": "20260214"},
            },
            {
                "Items": [{"race_date": "20260221"}],
            },
        ]
        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )

        result = provider.get_race_dates(
            from_date=date(2026, 2, 7), to_date=date(2026, 3, 7)
        )

        assert result == [date(2026, 2, 21), date(2026, 2, 14)]
        assert mock_table.scan.call_count == 2

    def test_ProjectionExpressionでrace_dateのみ取得する(self):
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": [{"race_date": "20260214"}]}
        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )

        provider.get_race_dates(from_date=date(2026, 2, 7), to_date=date(2026, 3, 7))

        call_kwargs = mock_table.scan.call_args[1]
        assert call_kwargs["ProjectionExpression"] == "race_date"
