"""HRDB レース取得バッチのテスト."""
import os
from unittest.mock import MagicMock, patch

import pytest


class TestHrdbRacesScraper:

    @patch.dict(os.environ, {
        "RACES_TABLE_NAME": "baken-kaigi-races",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_races_scraper.boto3")
    @patch("batch.hrdb_races_scraper._get_hrdb_client")
    def test_正常系_HRDB結果をDynamoDBに書き込む(self, mock_get_client, mock_boto3):
        from batch.hrdb_races_scraper import handler

        mock_client = MagicMock()
        mock_client.query.return_value = [
            {
                "OPDT": "20260215",
                "RCOURSECD": "06",
                "RNO": "11",
                "RNAME": "フェブラリーS",
                "TRACKCD": "23",
                "KYORI": "1600",
                "BABA": "1",
                "TOSU": "16",
                "GRADECD": "1",
                "JYOKENCD": "A3",
                "HTIME": "1540",
            },
            {
                "OPDT": "20260215",
                "RCOURSECD": "06",
                "RNO": "1",
                "RNAME": "1R",
                "TRACKCD": "11",
                "KYORI": "1200",
                "BABA": "1",
                "TOSU": "10",
                "GRADECD": "",
                "JYOKENCD": "",
                "HTIME": "1000",
            },
        ]
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_batch_writer = MagicMock()
        mock_batch_writer.__enter__ = MagicMock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = MagicMock(return_value=False)
        mock_table.batch_writer.return_value = mock_batch_writer
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = handler({"target_date": "20260215"}, None)

        assert result["status"] == "ok"
        assert result["count"] == 2
        assert mock_batch_writer.put_item.call_count == 2

        # 書き込まれたアイテムを検証
        calls = mock_batch_writer.put_item.call_args_list
        items = [call.kwargs["Item"] for call in calls]
        race_ids = {item["race_id"] for item in items}
        assert "20260215_06_11" in race_ids
        assert "20260215_06_01" in race_ids

    @patch.dict(os.environ, {
        "RACES_TABLE_NAME": "baken-kaigi-races",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_races_scraper.boto3")
    @patch("batch.hrdb_races_scraper._get_hrdb_client")
    def test_結果が0件の場合もエラーにならない(self, mock_get_client, mock_boto3):
        from batch.hrdb_races_scraper import handler

        mock_client = MagicMock()
        mock_client.query.return_value = []
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_batch_writer = MagicMock()
        mock_batch_writer.__enter__ = MagicMock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = MagicMock(return_value=False)
        mock_table.batch_writer.return_value = mock_batch_writer
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = handler({"target_date": "20260215"}, None)
        assert result["status"] == "ok"
        assert result["count"] == 0
        assert mock_batch_writer.put_item.call_count == 0

    @patch.dict(os.environ, {
        "RACES_TABLE_NAME": "baken-kaigi-races",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_races_scraper.boto3")
    @patch("batch.hrdb_races_scraper._get_hrdb_client")
    def test_target_date未指定時は翌日のデータを取得する(self, mock_get_client, mock_boto3):
        from batch.hrdb_races_scraper import handler

        mock_client = MagicMock()
        mock_client.query.return_value = []
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_batch_writer = MagicMock()
        mock_batch_writer.__enter__ = MagicMock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = MagicMock(return_value=False)
        mock_table.batch_writer.return_value = mock_batch_writer
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = handler({}, None)
        assert result["status"] == "ok"

        # SQLにOPDTの日付が含まれていることを確認
        sql_arg = mock_client.query.call_args[0][0]
        assert "OPDT" in sql_arg
