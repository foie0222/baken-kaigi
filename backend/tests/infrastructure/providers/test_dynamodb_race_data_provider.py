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
        assert result.venue == "東京"
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
        item1["race_number"] = Decimal("1")
        item2 = _make_race_item()
        item2["venue"] = "中山"
        item2["race_number"] = Decimal("3")
        item2["race_id"] = "202602140303"
        mock_table.query.return_value = {"Items": [item2, item1]}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_races_by_date(date(2026, 2, 14))

        assert len(result) == 2
        assert all(isinstance(r, RaceData) for r in result)
        # venue順 → race_number順
        assert result[0].venue == "中山"
        assert result[1].venue == "東京"

    def test_venueフィルタで絞り込める(self):
        mock_table = MagicMock()
        item_tokyo = _make_race_item()
        item_tokyo["venue"] = "東京"
        item_nakayama = _make_race_item()
        item_nakayama["venue"] = "中山"
        item_nakayama["race_id"] = "202602140303"
        mock_table.query.return_value = {"Items": [item_tokyo, item_nakayama]}

        provider = DynamoDbRaceDataProvider(
            races_table=mock_table, runners_table=MagicMock()
        )
        result = provider.get_races_by_date(date(2026, 2, 14), venue="東京")

        assert len(result) == 1
        assert result[0].venue == "東京"

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


class TestNotImplemented:
    """未実装メソッドのテスト."""

    def _make_provider(self) -> DynamoDbRaceDataProvider:
        return DynamoDbRaceDataProvider(
            races_table=MagicMock(), runners_table=MagicMock()
        )

    def test_get_jockey_statsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_jockey_stats("01234", "東京芝1600")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_pedigreeは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_pedigree("2020100001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_weight_historyは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_weight_history("2020100001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_race_weightsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_race_weights(RaceId("202602140505"))
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_jra_checksumは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_jra_checksum("05", "01", 2, 5)
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_race_datesは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_race_dates()
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_past_race_statsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_past_race_stats("芝", 1600)
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_jockey_infoは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_jockey_info("01234")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_jockey_stats_detailは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_jockey_stats_detail("01234")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_horse_performancesは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_horse_performances("2020100001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_horse_trainingは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_horse_training("2020100001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_extended_pedigreeは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_extended_pedigree("2020100001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_odds_historyは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_odds_history(RaceId("202602140505"))
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_running_stylesは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_running_styles(RaceId("202602140505"))
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_course_aptitudeは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_course_aptitude("2020100001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_trainer_infoは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_trainer_info("01234")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_trainer_stats_detailは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_trainer_stats_detail("01234")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_stallion_offspring_statsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_stallion_offspring_stats("2020100001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_gate_position_statsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_gate_position_stats("東京")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_race_resultsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_race_results(RaceId("202602140505"))
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_owner_infoは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_owner_info("00001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_owner_statsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_owner_stats("00001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_breeder_infoは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_breeder_info("00001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_breeder_statsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_breeder_stats("00001")
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass

    def test_get_all_oddsは未実装(self):
        provider = self._make_provider()
        try:
            provider.get_all_odds(RaceId("202602140505"))
            assert False, "NotImplementedError が発生しなかった"
        except NotImplementedError:
            pass
