"""HRDB 調教師マスタ同期バッチのテスト."""
import os
from unittest.mock import MagicMock, patch

import pytest


class TestHrdbTrainersSync:

    @patch.dict(os.environ, {
        "RUNNERS_TABLE_NAME": "baken-kaigi-runners",
        "TRAINERS_TABLE_NAME": "baken-kaigi-trainers",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_trainers_sync.boto3")
    @patch("batch.hrdb_trainers_sync.get_hrdb_client")
    def test_正常系_未登録の調教師をHRDBから取得して書き込む(
        self, mock_get_client, mock_boto3,
    ):
        from batch.hrdb_trainers_sync import handler

        mock_runners = MagicMock()
        mock_runners.scan.return_value = {
            "Items": [
                {"trainer_id": "T001"},
                {"trainer_id": "T002"},
            ]
        }

        mock_trainers = MagicMock()
        mock_trainers.get_item.return_value = {}
        mock_batch_writer = MagicMock()
        mock_batch_writer.__enter__ = MagicMock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = MagicMock(return_value=False)
        mock_trainers.batch_writer.return_value = mock_batch_writer

        def get_table(name):
            if "runners" in name:
                return mock_runners
            return mock_trainers

        mock_boto3.resource.return_value.Table.side_effect = get_table

        mock_client = MagicMock()
        mock_client.query.return_value = [
            {"TRNRCD": "T001", "TRNRNAME": "調教師1", "TRNRKANA": "チョウキョウシ1", "SHOZOKU": "美浦"},
            {"TRNRCD": "T002", "TRNRNAME": "調教師2", "TRNRKANA": "チョウキョウシ2", "SHOZOKU": "栗東"},
        ]
        mock_get_client.return_value = mock_client

        result = handler({}, None)
        assert result["status"] == "ok"
        assert result["count"] == 2
