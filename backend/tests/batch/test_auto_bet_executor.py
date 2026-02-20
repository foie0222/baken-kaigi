"""BetExecutor Lambda ハンドラのテスト."""
import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("TARGET_USER_ID", "test-user")

from batch.auto_bet_executor import handler, _run_pipeline, _fetch_predictions


class TestFetchPredictions:
    def test_DynamoDBからAI予想を取得(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "race_id": "202602210501",
                "source": "keiba-ai-navi",
                "predictions": [
                    {"horse_number": "1", "score": "80", "rank": "1"},
                    {"horse_number": "2", "score": "70", "rank": "2"},
                ],
            }
        }
        result = _fetch_predictions(mock_table, "202602210501")
        assert "keiba-ai-navi" in result
        assert result["keiba-ai-navi"][0]["horse_number"] == 1
        assert result["keiba-ai-navi"][0]["score"] == 80.0


class TestRunPipeline:
    def test_予想とオッズから買い目を生成(self):
        predictions = {
            "keiba-ai-navi": [
                {"horse_number": 1, "score": 90, "rank": 1},
                {"horse_number": 2, "score": 80, "rank": 2},
                {"horse_number": 3, "score": 70, "rank": 3},
                {"horse_number": 4, "score": 60, "rank": 4},
                {"horse_number": 5, "score": 50, "rank": 5},
            ],
            "umamax": [
                {"horse_number": 1, "score": 85, "rank": 1},
                {"horse_number": 2, "score": 75, "rank": 2},
                {"horse_number": 3, "score": 65, "rank": 3},
                {"horse_number": 4, "score": 55, "rank": 4},
                {"horse_number": 5, "score": 45, "rank": 5},
            ],
            "muryou-keiba-ai": [
                {"horse_number": 1, "score": 88, "rank": 1},
                {"horse_number": 3, "score": 78, "rank": 2},
                {"horse_number": 2, "score": 68, "rank": 3},
                {"horse_number": 5, "score": 58, "rank": 4},
                {"horse_number": 4, "score": 48, "rank": 5},
            ],
            "keiba-ai-athena": [
                {"horse_number": 1, "score": 92, "rank": 1},
                {"horse_number": 2, "score": 82, "rank": 2},
                {"horse_number": 3, "score": 72, "rank": 3},
                {"horse_number": 4, "score": 62, "rank": 4},
                {"horse_number": 5, "score": 52, "rank": 5},
            ],
        }
        odds = {
            "win": {
                "1": {"o": 3.5}, "2": {"o": 5.0}, "3": {"o": 8.0},
                "4": {"o": 15.0}, "5": {"o": 20.0},
            },
            "place": {
                "1": {"lo": 1.1, "mid": 1.5, "hi": 2.0},
                "2": {"lo": 2.0, "mid": 3.5, "hi": 5.0},
                "3": {"lo": 2.5, "mid": 4.5, "hi": 7.0},
                "4": {"lo": 3.0, "mid": 5.5, "hi": 8.0},
                "5": {"lo": 4.0, "mid": 7.0, "hi": 10.0},
            },
            "quinella": {"1-2": 12.0, "1-3": 18.0, "2-3": 25.0},
            "quinella_place": {"1-2": 5.0, "1-3": 8.0, "2-3": 12.0, "1-4": 15.0},
        }
        bets = _run_pipeline(predictions, odds)
        assert isinstance(bets, list)


class TestHandler:
    @patch("batch.auto_bet_executor._submit_bets")
    @patch("batch.auto_bet_executor._fetch_odds")
    @patch("batch.auto_bet_executor._fetch_predictions")
    def test_正常系_買い目なしでも正常終了(
        self, mock_preds, mock_odds, mock_submit
    ):
        mock_preds.return_value = {}  # 予想なし → 買い目0件
        event = {"race_id": "202602210501"}
        result = handler(event, None)
        assert result["status"] == "ok"
        assert result["bets_count"] == 0
        mock_submit.assert_not_called()
