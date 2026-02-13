"""DynamoDB読み出しクライアントのテスト."""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))


class TestGetRace:

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_レース情報を取得する(self, mock_get_ddb):
        from tools.dynamodb_client import get_race

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "race_id": "20260215_06_11",
                "race_date": "20260215",
                "race_name": "フェブラリーS",
                "distance": Decimal("1600"),
            }
        }
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_race("20260215_06_11")

        assert result is not None
        assert result["race_name"] == "フェブラリーS"
        mock_table.get_item.assert_called_once_with(
            Key={"race_date": "20260215", "race_id": "20260215_06_11"},
        )

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_存在しないレースでNoneを返す(self, mock_get_ddb):
        from tools.dynamodb_client import get_race

        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_race("99991231_99_99")
        assert result is None


class TestGetRunners:

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_出走馬リストを取得する(self, mock_get_ddb):
        from tools.dynamodb_client import get_runners

        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {"race_id": "20260215_06_11", "horse_number": Decimal("1"), "horse_name": "馬1"},
                {"race_id": "20260215_06_11", "horse_number": Decimal("2"), "horse_name": "馬2"},
            ]
        }
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_runners("20260215_06_11")

        assert len(result) == 2
        assert result[0]["horse_name"] == "馬1"

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_出走馬なしで空リストを返す(self, mock_get_ddb):
        from tools.dynamodb_client import get_runners

        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_runners("20260215_06_11")
        assert result == []


class TestGetHorsePerformances:

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_馬の過去成績を取得する(self, mock_get_ddb):
        from tools.dynamodb_client import get_horse_performances

        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {"horse_id": "2020100001", "race_date": "20260208", "finish_position": Decimal("1")},
                {"horse_id": "2020100001", "race_date": "20260201", "finish_position": Decimal("3")},
            ]
        }
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_horse_performances("2020100001", limit=5)

        assert len(result) == 2


class TestGetHorse:

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_馬情報を取得する(self, mock_get_ddb):
        from tools.dynamodb_client import get_horse

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"horse_id": "2020100001", "horse_name": "テスト馬", "sire_name": "テスト父"}
        }
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_horse("2020100001")

        assert result is not None
        assert result["horse_name"] == "テスト馬"
        mock_table.get_item.assert_called_once_with(
            Key={"horse_id": "2020100001", "sk": "info"},
        )

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_存在しない馬でNoneを返す(self, mock_get_ddb):
        from tools.dynamodb_client import get_horse

        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_horse("9999999999")
        assert result is None


class TestGetJockey:

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_騎手情報を取得する(self, mock_get_ddb):
        from tools.dynamodb_client import get_jockey

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"jockey_id": "01234", "jockey_name": "テスト騎手"}
        }
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_jockey("01234")

        assert result is not None
        assert result["jockey_name"] == "テスト騎手"


class TestGetTrainer:

    @patch("tools.dynamodb_client._get_dynamodb")
    def test_調教師情報を取得する(self, mock_get_ddb):
        from tools.dynamodb_client import get_trainer

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"trainer_id": "05678", "trainer_name": "テスト調教師"}
        }
        mock_get_ddb.return_value.Table.return_value = mock_table

        result = get_trainer("05678")

        assert result is not None
        assert result["trainer_name"] == "テスト調教師"
