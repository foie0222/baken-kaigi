"""HRDB 馬マスタ同期バッチのテスト."""
import os
from unittest.mock import MagicMock, call, patch

import pytest


class TestHrdbHorsesSync:

    @patch.dict(os.environ, {
        "RUNNERS_TABLE_NAME": "baken-kaigi-runners",
        "HORSES_TABLE_NAME": "baken-kaigi-horses",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_horses_sync.boto3")
    @patch("batch.hrdb_horses_sync.get_hrdb_client")
    def test_正常系_未登録の馬をHRDBから取得してDynamoDBに書き込む(
        self, mock_get_client, mock_boto3,
    ):
        from batch.hrdb_horses_sync import handler

        # runners テーブルモック
        mock_runners = MagicMock()
        mock_runners.scan.return_value = {
            "Items": [
                {"horse_id": "H001"},
                {"horse_id": "H002"},
                {"horse_id": "H003"},
            ]
        }

        # horses テーブルモック（H001は既存）
        mock_horses = MagicMock()
        mock_horses.get_item.side_effect = lambda **kwargs: (
            {"Item": {"horse_id": "H001"}}
            if kwargs["Key"]["horse_id"] == "H001"
            else {}
        )
        mock_batch_writer = MagicMock()
        mock_batch_writer.__enter__ = MagicMock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = MagicMock(return_value=False)
        mock_horses.batch_writer.return_value = mock_batch_writer

        # テーブルの切り替え
        def get_table(name):
            if "runners" in name:
                return mock_runners
            return mock_horses

        mock_boto3.resource.return_value.Table.side_effect = get_table

        # HRDB client
        mock_client = MagicMock()
        mock_client.query.return_value = [
            {"BLDNO": "H002", "BAMEI": "馬2", "FTNAME": "父2", "MTNAME": "母2",
             "BMSTNAME": "BMS2", "BNEN": "2021", "SEX": "1", "KEIRO": "01"},
            {"BLDNO": "H003", "BAMEI": "馬3", "FTNAME": "父3", "MTNAME": "母3",
             "BMSTNAME": "BMS3", "BNEN": "2022", "SEX": "2", "KEIRO": "02"},
        ]
        mock_get_client.return_value = mock_client

        result = handler({}, None)

        assert result["status"] == "ok"
        assert result["count"] == 2
        assert mock_batch_writer.put_item.call_count == 2

    @patch.dict(os.environ, {
        "RUNNERS_TABLE_NAME": "baken-kaigi-runners",
        "HORSES_TABLE_NAME": "baken-kaigi-horses",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_horses_sync.boto3")
    def test_全馬が登録済みの場合はHRDBを呼ばない(self, mock_boto3):
        from batch.hrdb_horses_sync import handler

        mock_runners = MagicMock()
        mock_runners.scan.return_value = {
            "Items": [{"horse_id": "H001"}],
        }

        mock_horses = MagicMock()
        mock_horses.get_item.return_value = {"Item": {"horse_id": "H001"}}

        def get_table(name):
            if "runners" in name:
                return mock_runners
            return mock_horses

        mock_boto3.resource.return_value.Table.side_effect = get_table

        result = handler({}, None)
        assert result["status"] == "ok"
        assert result["count"] == 0
