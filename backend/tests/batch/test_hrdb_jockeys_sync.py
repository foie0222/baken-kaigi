"""HRDB 騎手マスタ同期バッチのテスト."""
import os
from unittest.mock import MagicMock, patch

import pytest


class TestHrdbJockeysSync:

    @patch.dict(os.environ, {
        "RUNNERS_TABLE_NAME": "baken-kaigi-runners",
        "JOCKEYS_TABLE_NAME": "baken-kaigi-jockeys",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_jockeys_sync.boto3")
    @patch("batch.hrdb_jockeys_sync.get_hrdb_client")
    def test_正常系_未登録の騎手をHRDBから取得して書き込む(
        self, mock_get_client, mock_boto3,
    ):
        from batch.hrdb_jockeys_sync import handler

        mock_runners = MagicMock()
        mock_runners.scan.return_value = {
            "Items": [
                {"jockey_id": "J001"},
                {"jockey_id": "J002"},
            ]
        }

        mock_jockeys = MagicMock()
        mock_jockeys.get_item.return_value = {}
        mock_batch_writer = MagicMock()
        mock_batch_writer.__enter__ = MagicMock(return_value=mock_batch_writer)
        mock_batch_writer.__exit__ = MagicMock(return_value=False)
        mock_jockeys.batch_writer.return_value = mock_batch_writer

        def get_table(name):
            if "runners" in name:
                return mock_runners
            return mock_jockeys

        mock_boto3.resource.return_value.Table.side_effect = get_table

        mock_client = MagicMock()
        mock_client.query.return_value = [
            {"JKYCD": "J001", "JKYNAME": "騎手1", "JKYKANA": "キシュ1", "SHOZOKU": "美浦"},
            {"JKYCD": "J002", "JKYNAME": "騎手2", "JKYKANA": "キシュ2", "SHOZOKU": "栗東"},
        ]
        mock_get_client.return_value = mock_client

        result = handler({}, None)
        assert result["status"] == "ok"
        assert result["count"] == 2
