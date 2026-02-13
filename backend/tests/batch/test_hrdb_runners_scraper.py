"""HRDB 出走馬取得バッチのテスト."""
import os
from unittest.mock import MagicMock, patch

import pytest


class TestHrdbRunnersScraper:

    @patch.dict(os.environ, {
        "RUNNERS_TABLE_NAME": "baken-kaigi-runners",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_runners_scraper.boto3")
    @patch("batch.hrdb_runners_scraper._get_hrdb_client")
    def test_正常系_HRDB結果をDynamoDBに書き込む(self, mock_get_client, mock_boto3):
        from batch.hrdb_runners_scraper import handler

        mock_client = MagicMock()
        mock_client.query.return_value = [
            {
                "OPDT": "20260215",
                "RCOURSECD": "06",
                "RNO": "11",
                "UMABAN": "3",
                "BAMEI": "テスト馬",
                "BLDNO": "2020100001",
                "JKYCD": "01234",
                "JKYNAME": "テスト騎手",
                "TRNRCD": "05678",
                "ODDS": "5.6",
                "NINKI": "2",
                "WAKUBAN": "2",
                "FUTAN": "57.0",
                "KAKUTEI": "0",
                "TIME": "",
                "AGARI3F": "",
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
        assert result["count"] == 1
        assert mock_batch_writer.put_item.call_count == 1

        item = mock_batch_writer.put_item.call_args.kwargs["Item"]
        assert item["race_id"] == "20260215_06_11"
        assert item["horse_number"] == 3
        assert item["horse_name"] == "テスト馬"
        assert item["horse_id"] == "2020100001"
