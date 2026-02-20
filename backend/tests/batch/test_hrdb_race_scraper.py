"""HRDBレースデータバッチスクレイパーのテスト."""

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.hrdb_race_scraper import (
    _parse_run_time,
    _validate_date,
    convert_race_row,
    convert_runner_row,
    handler,
)

JST = timezone(timedelta(hours=9))


def _make_race_row(**overrides) -> dict:
    """テスト用RACEMSTレコードを生成."""
    row = {
        "OPDT": "20260222",
        "RCOURSECD": "05",
        "RNO": "11",
        "RNMHON": "フェブラリーステークス  ",
        "GCD": "G1  ",
        "DIST": "1600",
        "TRACKCD": "23",
        "ENTNUM": "16",
        "RUNNUM": "16",
        "POSTTM": "1540",
        "WEATHERCD": "1",
        "TSTATCD": "1",
        "DSTATCD": "2",
        "KAI": "01",
        "NITIME": "08",
    }
    row.update(overrides)
    return row


def _make_runner_row(**overrides) -> dict:
    """テスト用RACEDTLレコードを生成."""
    row = {
        "OPDT": "20260222",
        "RCOURSECD": "05",
        "RNO": "11",
        "UMANO": "1",
        "BLDNO": "2019104567",
        "HSNM": "レモンポップ      ",
        "WAKNO": "1",
        "SEXCD": "1",
        "AGE": "7",
        "JKYCD": "05386",
        "JKYNM4": "坂井瑠星  ",
        "TRNRCD": "01128",
        "TRNRNM4": "田中博康  ",
        "FTNWGHT": "570",
        "FIXPLC": "01",
        "RUNTM": "1326",
        "TANODDS": "0034",
        "TANNINKI": "01",
    }
    row.update(overrides)
    return row


class TestConvertRaceRow:
    """convert_race_row のテスト."""

    def test_基本変換(self):
        """全フィールドが正しくマッピングされること."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_race_row()

        result = convert_race_row(row, scraped_at)

        assert result["race_date"] == "20260222"
        assert result["race_id"] == "202602220511"
        assert result["venue"] == "東京"
        assert result["venue_code"] == "05"
        assert result["race_number"] == 11
        assert result["race_name"] == "フェブラリーステークス"
        assert result["grade"] == "G1"
        assert result["distance"] == 1600
        assert result["track_type"] == "ダート"
        assert result["track_code"] == "23"
        assert result["horse_count"] == 16
        assert result["run_count"] == 16
        assert result["post_time"] == "1540"
        assert result["weather_code"] == "1"
        assert result["turf_condition_code"] == "1"
        assert result["dirt_condition_code"] == "2"
        assert result["kaisai_kai"] == "01"
        assert result["kaisai_nichime"] == "08"
        assert result["scraped_at"] == scraped_at.isoformat()
        # TTL: scraped_at + 14日
        expected_ttl = int((scraped_at + timedelta(days=14)).timestamp())
        assert result["ttl"] == expected_ttl

    def test_ダートトラック(self):
        """TRACKCD先頭"2" → "ダート"."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_race_row(TRACKCD="23")

        result = convert_race_row(row, scraped_at)

        assert result["track_type"] == "ダート"

    def test_障害トラック(self):
        """TRACKCD先頭"5" → "障害"."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_race_row(TRACKCD="54")

        result = convert_race_row(row, scraped_at)

        assert result["track_type"] == "障害"

    def test_未来レースで数値フィールドが空(self):
        """RUNNUM等が空文字の未来レースでもエラーにならないこと."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_race_row(RUNNUM="", ENTNUM="", DIST="")

        result = convert_race_row(row, scraped_at)

        assert result["race_id"] == "202602220511"
        assert "run_count" not in result
        assert "horse_count" not in result
        assert "distance" not in result


class TestConvertRunnerRow:
    """convert_runner_row のテスト."""

    def test_基本変換(self):
        """全フィールドが正しくマッピングされること."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_runner_row()

        result = convert_runner_row(row, scraped_at)

        assert result["race_id"] == "202602220511"
        assert result["horse_number"] == "01"
        assert result["race_date"] == "20260222"
        assert result["horse_id"] == "2019104567"
        assert result["horse_name"] == "レモンポップ"
        assert result["waku_ban"] == 1
        assert result["sex_code"] == "1"
        assert result["age"] == 7
        assert result["jockey_id"] == "05386"
        assert result["jockey_name"] == "坂井瑠星"
        assert result["trainer_id"] == "01128"
        assert result["trainer_name"] == "田中博康"
        assert result["weight_carried"] == Decimal("57.0")
        assert result["finish_position"] == 1
        assert result["time"] == "1:32.6"
        assert result["odds"] == Decimal("3.4")
        assert result["popularity"] == 1
        assert result["scraped_at"] == scraped_at.isoformat()
        expected_ttl = int((scraped_at + timedelta(days=14)).timestamp())
        assert result["ttl"] == expected_ttl

    def test_未確定の着順(self):
        """FIXPLC="00", RUNTM="0000" → None（フィルタ済み）."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_runner_row(FIXPLC="00", RUNTM="0000", TANODDS="0000", TANNINKI="00")

        result = convert_runner_row(row, scraped_at)

        assert "finish_position" not in result
        assert "time" not in result
        assert "odds" not in result
        assert "popularity" not in result

    def test_走破タイム変換(self):
        """RUNTM "1455" → "1:45.5"."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_runner_row(RUNTM="1455")

        result = convert_runner_row(row, scraped_at)

        assert result["time"] == "1:45.5"

    def test_None値がフィルタされる(self):
        """DynamoDBはNoneを受け付けないため、None値はフィルタされること."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_runner_row(FIXPLC="00", RUNTM="0000", TANODDS="0000", TANNINKI="00")

        result = convert_runner_row(row, scraped_at)

        for key, value in result.items():
            assert value is not None, f"key={key} has None value"


class TestParseRunTime:
    """_parse_run_time のテスト."""

    def test_正常変換(self):
        assert _parse_run_time("1326") == "1:32.6"

    def test_1分45秒5(self):
        assert _parse_run_time("1455") == "1:45.5"

    def test_ゼロ(self):
        assert _parse_run_time("0000") is None

    def test_空文字(self):
        assert _parse_run_time("") is None

    def test_3桁の不正データ(self):
        assert _parse_run_time("132") is None

    def test_5桁の不正データ(self):
        assert _parse_run_time("13265") is None

    def test_非数字を含むデータ(self):
        assert _parse_run_time("1a26") is None


class TestConvertRunnerRowEdgeCases:
    """convert_runner_row のエッジケーステスト."""

    def test_斤量ゼロはNone(self):
        """FTNWGHT="0" → weight_carriedはNone（フィルタ済み）."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_runner_row(FTNWGHT="0")
        result = convert_runner_row(row, scraped_at)
        assert "weight_carried" not in result

    def test_斤量空文字はNone(self):
        """FTNWGHT="" → weight_carriedはNone（フィルタ済み）."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_runner_row(FTNWGHT="")
        result = convert_runner_row(row, scraped_at)
        assert "weight_carried" not in result

    def test_未来レースで結果フィールドが空(self):
        """未来レースではFIXPLC,RUNTM,TANODDS,TANNINKI等が空でもエラーにならない."""
        scraped_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=JST)
        row = _make_runner_row(
            FIXPLC="", RUNTM="", TANODDS="", TANNINKI="",
            FTNWGHT="", WAKNO="", AGE="",
        )
        result = convert_runner_row(row, scraped_at)
        assert result["race_id"] == "202602220511"
        assert result["horse_number"] == "01"
        assert "finish_position" not in result
        assert "time" not in result
        assert "odds" not in result
        assert "popularity" not in result
        assert "weight_carried" not in result
        assert "waku_ban" not in result
        assert "age" not in result


class TestValidateDate:
    """_validate_date のテスト."""

    def test_正常な日付(self):
        assert _validate_date("20260222") == "20260222"

    def test_数字以外を含む文字列(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            _validate_date("2026-02-22")

    def test_桁数不足(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            _validate_date("202602")

    def test_SQLインジェクション(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            _validate_date("'; DROP TABLE RACEMST; --")


class TestHandler:
    """handler のテスト."""

    @patch("batch.hrdb_race_scraper.get_runners_table")
    @patch("batch.hrdb_race_scraper.get_races_table")
    @patch("batch.hrdb_race_scraper.get_hrdb_client")
    def test_翌日データ取得の正常系(
        self, mock_get_client, mock_get_races_table, mock_get_runners_table
    ):
        """翌日のレースデータを取得してDynamoDBに保存."""
        # HrdbClientモック
        mock_client = MagicMock()
        race_rows = [_make_race_row()]
        runner_rows = [_make_runner_row()]
        mock_client.query_dual.return_value = (race_rows, runner_rows)
        mock_get_client.return_value = mock_client

        # DynamoDBテーブルモック（batch_writer対応）
        mock_races = MagicMock()
        mock_race_batch = MagicMock()
        mock_races.batch_writer.return_value.__enter__ = MagicMock(return_value=mock_race_batch)
        mock_races.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_races_table.return_value = mock_races

        mock_runners = MagicMock()
        mock_runner_batch = MagicMock()
        mock_runners.batch_writer.return_value.__enter__ = MagicMock(return_value=mock_runner_batch)
        mock_runners.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_runners_table.return_value = mock_runners

        # 実行
        result = handler({"offset_days": 1}, None)

        # 検証
        assert result["statusCode"] == 200
        body = result["body"]
        assert body["success"] is True
        assert body["races_saved"] == 1
        assert body["runners_saved"] == 1

        # batch_writerへの書き込み検証
        mock_race_batch.put_item.assert_called_once()
        mock_runner_batch.put_item.assert_called_once()

        # put_itemの引数検証
        race_item = mock_race_batch.put_item.call_args[1]["Item"]
        assert race_item["race_id"] == "202602220511"
        assert race_item["race_name"] == "フェブラリーステークス"

        runner_item = mock_runner_batch.put_item.call_args[1]["Item"]
        assert runner_item["race_id"] == "202602220511"
        assert runner_item["horse_number"] == "01"
        assert runner_item["horse_name"] == "レモンポップ"

        # query_dualの呼び出し検証
        mock_client.query_dual.assert_called_once()
        sql1, sql2 = mock_client.query_dual.call_args[0]
        assert "RACEMST" in sql1
        assert "RACEDTL" in sql2
