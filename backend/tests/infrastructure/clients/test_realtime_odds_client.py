"""リアルタイムオッズクライアントのテスト."""
from unittest.mock import patch, MagicMock
import pytest
from src.infrastructure.clients.realtime_odds_client import RealtimeOddsClient


class TestRealtimeOddsClient:

    def _make_client(self) -> RealtimeOddsClient:
        return RealtimeOddsClient(api_base_url="https://api.gamble-os.net")

    @patch("src.infrastructure.clients.realtime_odds_client.requests.get")
    def test_正常系_単勝オッズを取得(self, mock_get):
        """レースIDを指定して単勝オッズを取得."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ret": "0",
            "odds": [
                {"horse_number": 1, "win_odds": 3.5, "place_odds_min": 1.5, "place_odds_max": 2.0},
                {"horse_number": 2, "win_odds": 5.0, "place_odds_min": 2.0, "place_odds_max": 3.0},
            ]
        }
        mock_get.return_value = mock_response

        client = self._make_client()
        result = client.get_win_odds("20260215_06_11")

        assert len(result) == 2
        assert result[0]["horse_number"] == 1
        assert result[0]["win_odds"] == 3.5

    @patch("src.infrastructure.clients.realtime_odds_client.requests.get")
    def test_正常系_オッズ変動履歴を取得(self, mock_get):
        """レースIDを指定してオッズ変動履歴を取得."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ret": "0",
            "history": [
                {"timestamp": "2026-02-15T10:00:00", "horse_number": 1, "odds": 4.0},
                {"timestamp": "2026-02-15T11:00:00", "horse_number": 1, "odds": 3.5},
            ]
        }
        mock_get.return_value = mock_response

        client = self._make_client()
        result = client.get_odds_history("20260215_06_11")

        assert len(result) == 2

    @patch("src.infrastructure.clients.realtime_odds_client.requests.get")
    def test_APIエラー時に空リストを返す(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ret": "1", "msg": "Data not found"}
        mock_get.return_value = mock_response

        client = self._make_client()
        result = client.get_win_odds("20260215_06_11")

        assert result == []

    @patch("src.infrastructure.clients.realtime_odds_client.requests.get")
    def test_ネットワークエラー時に空リストを返す(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")

        client = self._make_client()
        result = client.get_win_odds("20260215_06_11")

        assert result == []
