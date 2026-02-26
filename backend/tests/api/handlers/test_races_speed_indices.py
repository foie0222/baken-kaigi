"""スピード指数データAPI ハンドラーテスト."""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.api.handlers.races import get_speed_indices


@pytest.fixture
def mock_dynamodb_table():
    """DynamoDB テーブルのモックをセットアップする."""
    with patch("src.api.handlers.races.boto3") as mock_boto3:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        yield mock_table


class TestGetSpeedIndices:
    """get_speed_indices ハンドラーのテスト."""

    def test_race_idがない場合は400を返す(self):
        """race_idがない場合は400エラーを返す."""
        event = {"pathParameters": {}}
        result = get_speed_indices(event, None)
        assert result["statusCode"] == 400

    def test_データが見つからない場合は404を返す(self, mock_dynamodb_table):
        """スピード指数データがない場合は404を返す."""
        mock_dynamodb_table.query.return_value = {"Items": []}
        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_speed_indices(event, None)
        assert result["statusCode"] == 404

    def test_正常なスピード指数データを返す(self, mock_dynamodb_table):
        """正常なスピード指数データをソース別にグルーピングして返す."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {
                    "race_id": "202401010101",
                    "source": "jiro8-speed",
                    "indices": [
                        {"horse_number": Decimal("1"), "speed_index": Decimal("78.5"), "rank": Decimal("1")},
                        {"horse_number": Decimal("4"), "speed_index": Decimal("72.0"), "rank": Decimal("2")},
                    ],
                },
                {
                    "race_id": "202401010101",
                    "source": "kichiuma-speed",
                    "indices": [
                        {"horse_number": Decimal("4"), "speed_index": Decimal("80.0"), "rank": Decimal("1")},
                        {"horse_number": Decimal("1"), "speed_index": Decimal("75.0"), "rank": Decimal("2")},
                    ],
                },
            ],
        }

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_speed_indices(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["race_id"] == "202401010101"
        assert "jiro8-speed" in body["indices"]
        assert "kichiuma-speed" in body["indices"]
        assert len(body["indices"]["jiro8-speed"]) == 2
        assert body["indices"]["jiro8-speed"][0]["horse_number"] == 1
        assert body["indices"]["jiro8-speed"][0]["speed_index"] == 78.5
        assert body["indices"]["jiro8-speed"][0]["rank"] == 1

    def test_Decimal型がfloatとintに変換される(self, mock_dynamodb_table):
        """DynamoDB の Decimal 型が適切に変換される."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {
                    "race_id": "202401010101",
                    "source": "daily-speed",
                    "indices": [
                        {"horse_number": Decimal("7"), "speed_index": Decimal("65.8"), "rank": Decimal("3")},
                    ],
                },
            ],
        }

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_speed_indices(event, None)

        body = json.loads(result["body"])
        idx = body["indices"]["daily-speed"][0]
        # Decimal("7") -> int(7), Decimal("65.8") -> float(65.8), Decimal("3") -> int(3)
        assert isinstance(idx["horse_number"], int)
        assert isinstance(idx["speed_index"], float)
        assert isinstance(idx["rank"], int)

    def test_DynamoDBエラー時に500を返す(self, mock_dynamodb_table):
        """DynamoDB クエリ失敗時に500エラーを返す."""
        mock_dynamodb_table.query.side_effect = Exception("DynamoDB error")
        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_speed_indices(event, None)
        assert result["statusCode"] == 500

    def test_CORSヘッダーが含まれる(self, mock_dynamodb_table):
        """レスポンスにCORSヘッダーが含まれる."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {
                    "race_id": "202401010101",
                    "source": "jiro8-speed",
                    "indices": [],
                },
            ],
        }

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_speed_indices(event, None)

        assert "Access-Control-Allow-Origin" in result["headers"]
        assert "Access-Control-Allow-Methods" in result["headers"]
