"""AI予想データ取得ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.ai_prediction import get_ai_prediction, list_ai_predictions_for_date


@pytest.fixture
def mock_dynamodb_table():
    """DynamoDBテーブルのモック."""
    with patch("tools.ai_prediction.get_dynamodb_table") as mock:
        table = MagicMock()
        mock.return_value = table
        yield table


class TestGetAiPrediction:
    """get_ai_prediction ツールのテスト."""

    def test_正常なデータ取得(self, mock_dynamodb_table):
        """正常系: DynamoDBからデータを取得できる."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "race_id": "20260131_05_11",
                "source": "ai-shisu",
                "venue": "東京",
                "race_number": 11,
                "predictions": [
                    {"rank": 1, "score": 691, "horse_number": 8, "horse_name": "ピースワンデュック"},
                    {"rank": 2, "score": 650, "horse_number": 3, "horse_name": "テスト馬"},
                ],
                "scraped_at": "2026-01-31T06:00:00+09:00",
                "ttl": 1738483200,
            }
        }

        result = get_ai_prediction(race_id="20260131_05_11")

        assert result["race_id"] == "20260131_05_11"
        assert result["source"] == "ai-shisu"
        assert result["venue"] == "東京"
        assert result["race_number"] == 11
        assert len(result["predictions"]) == 2
        assert result["predictions"][0]["rank"] == 1
        assert result["predictions"][0]["score"] == 691
        assert "ttl" not in result  # TTLは返さない
        assert "error" not in result

    def test_データが見つからない場合(self, mock_dynamodb_table):
        """異常系: データが存在しない場合はエラーメッセージを返す."""
        mock_dynamodb_table.get_item.return_value = {}

        result = get_ai_prediction(race_id="20260131_05_99")

        assert result["race_id"] == "20260131_05_99"
        assert result["source"] == "ai-shisu"
        assert "error" in result
        assert "AI予想データが見つかりません" in result["error"]
        assert result["predictions"] == []

    def test_DynamoDBエラー時(self, mock_dynamodb_table):
        """異常系: DynamoDBでエラーが発生した場合."""
        from botocore.exceptions import ClientError
        mock_dynamodb_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
            "GetItem"
        )

        result = get_ai_prediction(race_id="20260131_05_11")

        assert "error" in result
        assert "DynamoDBエラー" in result["error"]
        assert result["predictions"] == []

    def test_カスタムソース指定(self, mock_dynamodb_table):
        """正常系: カスタムソースを指定した場合."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "race_id": "20260131_05_11",
                "source": "custom-source",
                "venue": "東京",
                "race_number": 11,
                "predictions": [],
                "scraped_at": "2026-01-31T06:00:00+09:00",
            }
        }

        result = get_ai_prediction(race_id="20260131_05_11", source="custom-source")

        mock_dynamodb_table.get_item.assert_called_once_with(
            Key={"race_id": "20260131_05_11", "source": "custom-source"}
        )
        assert result["source"] == "custom-source"


class TestListAiPredictionsForDate:
    """list_ai_predictions_for_date ツールのテスト."""

    def test_日付でデータ一覧取得(self, mock_dynamodb_table):
        """正常系: 指定日のデータ一覧を取得できる."""
        mock_dynamodb_table.scan.return_value = {
            "Items": [
                {
                    "race_id": "20260131_05_11",
                    "source": "ai-shisu",
                    "venue": "東京",
                    "race_number": 11,
                    "predictions": [
                        {"rank": 1, "score": 691, "horse_number": 8, "horse_name": "馬A"},
                        {"rank": 2, "score": 650, "horse_number": 3, "horse_name": "馬B"},
                        {"rank": 3, "score": 600, "horse_number": 5, "horse_name": "馬C"},
                        {"rank": 4, "score": 550, "horse_number": 1, "horse_name": "馬D"},
                    ],
                    "scraped_at": "2026-01-31T06:00:00+09:00",
                },
                {
                    "race_id": "20260131_08_12",
                    "source": "ai-shisu",
                    "venue": "京都",
                    "race_number": 12,
                    "predictions": [
                        {"rank": 1, "score": 700, "horse_number": 1, "horse_name": "馬X"},
                    ],
                    "scraped_at": "2026-01-31T06:00:00+09:00",
                },
            ]
        }

        result = list_ai_predictions_for_date(date="20260131")

        assert result["date"] == "20260131"
        assert result["source"] == "ai-shisu"
        assert result["total_count"] == 2
        assert len(result["races"]) == 2

        # top_predictionsは上位3頭のみ
        tokyo_race = next(r for r in result["races"] if r["venue"] == "東京")
        assert len(tokyo_race["top_predictions"]) == 3

        kyoto_race = next(r for r in result["races"] if r["venue"] == "京都")
        assert len(kyoto_race["top_predictions"]) == 1

    def test_データがない場合(self, mock_dynamodb_table):
        """正常系: 指定日のデータがない場合."""
        mock_dynamodb_table.scan.return_value = {"Items": []}

        result = list_ai_predictions_for_date(date="20260201")

        assert result["date"] == "20260201"
        assert result["total_count"] == 0
        assert result["races"] == []
        assert "error" not in result

    def test_レースがソートされる(self, mock_dynamodb_table):
        """正常系: レースが競馬場名・レース番号でソートされる."""
        mock_dynamodb_table.scan.return_value = {
            "Items": [
                {"race_id": "20260131_05_12", "source": "ai-shisu", "venue": "東京", "race_number": 12, "predictions": []},
                {"race_id": "20260131_08_11", "source": "ai-shisu", "venue": "京都", "race_number": 11, "predictions": []},
                {"race_id": "20260131_05_11", "source": "ai-shisu", "venue": "東京", "race_number": 11, "predictions": []},
            ]
        }

        result = list_ai_predictions_for_date(date="20260131")

        # 京都が先（あいうえお順）、その後東京
        assert result["races"][0]["venue"] == "京都"
        assert result["races"][1]["venue"] == "東京"
        assert result["races"][1]["race_number"] == 11
        assert result["races"][2]["venue"] == "東京"
        assert result["races"][2]["race_number"] == 12
