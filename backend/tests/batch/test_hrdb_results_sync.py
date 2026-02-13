"""HRDB レース結果更新バッチのテスト."""
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestHrdbResultsSync:

    @patch.dict(os.environ, {
        "RUNNERS_TABLE_NAME": "baken-kaigi-runners",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_results_sync.boto3")
    @patch("batch.hrdb_results_sync.get_hrdb_client")
    def test_正常系_確定済みレース結果をDynamoDBに書き込む(
        self, mock_get_client, mock_boto3,
    ):
        from batch.hrdb_results_sync import handler

        mock_client = MagicMock()
        mock_client.query.return_value = [
            {
                "OPDT": "20260208",
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
                "KAKUTEI": "1",
                "TIME": "1353",
                "AGARI3F": "345",
            },
            {
                "OPDT": "20260208",
                "RCOURSECD": "06",
                "RNO": "11",
                "UMABAN": "5",
                "BAMEI": "テスト馬2",
                "BLDNO": "2020100002",
                "JKYCD": "01235",
                "JKYNAME": "テスト騎手2",
                "TRNRCD": "05679",
                "ODDS": "12.3",
                "NINKI": "5",
                "WAKUBAN": "4",
                "FUTAN": "55.0",
                "KAKUTEI": "2",
                "TIME": "1355",
                "AGARI3F": "348",
            },
        ]
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_batch_writer = MagicMock()
        mock_batch_writer.__enter__ = MagicMock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = MagicMock(return_value=False)
        mock_table.batch_writer.return_value = mock_batch_writer
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = handler({
            "from_date": "20260208",
            "to_date": "20260208",
        }, None)

        assert result["status"] == "ok"
        assert result["count"] == 2
        assert mock_batch_writer.put_item.call_count == 2

        # 確定着順が含まれていることを検証
        calls = mock_batch_writer.put_item.call_args_list
        items = [call.kwargs["Item"] for call in calls]
        positions = {item["finish_position"] for item in items}
        assert 1 in positions
        assert 2 in positions

    @patch.dict(os.environ, {
        "RUNNERS_TABLE_NAME": "baken-kaigi-runners",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_results_sync.boto3")
    @patch("batch.hrdb_results_sync.get_hrdb_client")
    def test_日付未指定時は前週月曜から日曜までを対象にする(
        self, mock_get_client, mock_boto3,
    ):
        from batch.hrdb_results_sync import handler

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
        assert result["count"] == 0

        # SQLに BETWEEN が含まれることを確認
        sql_arg = mock_client.query.call_args[0][0]
        assert "BETWEEN" in sql_arg
        assert "KAKUTEI > 0" in sql_arg
