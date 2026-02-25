"""AI予想データAPI ハンドラーテスト."""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.api.handlers.races import get_ai_predictions


@pytest.fixture
def mock_dynamodb_table():
    """DynamoDB テーブルのモックをセットアップする."""
    with patch("src.api.handlers.races.boto3") as mock_boto3:
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        yield mock_table


class TestGetAiPredictions:
    """get_ai_predictions ハンドラーのテスト."""

    def test_race_idがない場合は400を返す(self):
        """race_idがない場合は400エラーを返す."""
        event = {"pathParameters": {}}
        result = get_ai_predictions(event, None)
        assert result["statusCode"] == 400

    def test_データが見つからない場合は404を返す(self, mock_dynamodb_table):
        """AI予想データがない場合は404を返す."""
        mock_dynamodb_table.query.return_value = {"Items": []}
        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_ai_predictions(event, None)
        assert result["statusCode"] == 404

    def test_正常なAI予想データを返す(self, mock_dynamodb_table):
        """正常なAI予想データをソース別にグルーピングして返す."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {
                    "race_id": "202401010101",
                    "source": "ai-shisu",
                    "predictions": [
                        {"horse_number": Decimal("1"), "score": Decimal("85.5"), "rank": Decimal("1")},
                        {"horse_number": Decimal("3"), "score": Decimal("72.0"), "rank": Decimal("2")},
                    ],
                },
                {
                    "race_id": "202401010101",
                    "source": "keiba-ai-athena",
                    "predictions": [
                        {"horse_number": Decimal("3"), "score": Decimal("90.0"), "rank": Decimal("1")},
                        {"horse_number": Decimal("1"), "score": Decimal("80.0"), "rank": Decimal("2")},
                    ],
                },
            ],
        }

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_ai_predictions(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["race_id"] == "202401010101"
        assert "ai-shisu" in body["predictions"]
        assert "keiba-ai-athena" in body["predictions"]
        assert len(body["predictions"]["ai-shisu"]) == 2
        assert body["predictions"]["ai-shisu"][0]["horse_number"] == 1
        assert body["predictions"]["ai-shisu"][0]["score"] == 85.5
        assert body["predictions"]["ai-shisu"][0]["rank"] == 1

    def test_Decimal型がfloatとintに変換される(self, mock_dynamodb_table):
        """DynamoDB の Decimal 型が適切に変換される."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {
                    "race_id": "202401010101",
                    "source": "umamax",
                    "predictions": [
                        {"horse_number": Decimal("5"), "score": Decimal("78.3"), "rank": Decimal("1")},
                    ],
                },
            ],
        }

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_ai_predictions(event, None)

        body = json.loads(result["body"])
        pred = body["predictions"]["umamax"][0]
        # Decimal("5") -> int(5), Decimal("78.3") -> float(78.3), Decimal("1") -> int(1)
        assert isinstance(pred["horse_number"], int)
        assert isinstance(pred["score"], float)
        assert isinstance(pred["rank"], int)

    def test_DynamoDBエラー時に500を返す(self, mock_dynamodb_table):
        """DynamoDB クエリ失敗時に500エラーを返す."""
        mock_dynamodb_table.query.side_effect = Exception("DynamoDB error")
        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_ai_predictions(event, None)
        assert result["statusCode"] == 500

    def test_CORSヘッダーが含まれる(self, mock_dynamodb_table):
        """レスポンスにCORSヘッダーが含まれる."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {
                    "race_id": "202401010101",
                    "source": "ai-shisu",
                    "predictions": [],
                },
            ],
        }

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_ai_predictions(event, None)

        assert "Access-Control-Allow-Origin" in result["headers"]
        assert "Access-Control-Allow-Methods" in result["headers"]
