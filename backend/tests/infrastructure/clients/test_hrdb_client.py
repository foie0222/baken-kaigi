"""HRDB-APIクライアントのテスト."""
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.clients.hrdb_client import HrdbApiError, HrdbClient


class TestHrdbClientQuery:
    """HrdbClient.query() のテスト."""

    def _make_client(self) -> HrdbClient:
        return HrdbClient(
            club_id="TEST_CLUB",
            club_password="TEST_PASS",
            api_domain="https://api.example.com",
        )

    def test_正常系_SQL実行でCSV結果をdictリストで返す(self):
        """SQL送信→ポーリング→CSV取得の正常フロー."""
        client = self._make_client()

        # Phase 1: select → キューID取得
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {
            "ret1": "Q12345",
            "msg1": "",
            "ret": "0",
            "msg": "",
        }

        # Phase 2: state → 処理完了
        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {
            "ret1": "2",
            "msg1": "",
            "ret": "0",
            "msg": "",
        }

        # Phase 3: getcsv → CSV取得
        csv_data = "OPDT,RCOURSECD,RNO\n20260215,06,01\n20260215,06,02\n"
        csv_response = MagicMock()
        csv_response.status_code = 200
        csv_response.text = csv_data

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [submit_response, poll_response, csv_response]
            result = client.query("SELECT OPDT, RCOURSECD, RNO FROM RACEMST")

        assert len(result) == 2
        assert result[0]["OPDT"] == "20260215"
        assert result[0]["RCOURSECD"] == "06"
        assert result[1]["RNO"] == "02"

    def test_SQL送信エラーで例外を送出する(self):
        """SQL送信が失敗した場合."""
        client = self._make_client()

        error_response = MagicMock()
        error_response.status_code = 200
        error_response.json.return_value = {
            "ret1": "-100",
            "msg1": "SQL syntax error",
            "ret": "-100",
            "msg": "Parameters error.",
        }

        with patch("requests.post", return_value=error_response):
            with pytest.raises(HrdbApiError, match="Parameters error"):
                client.query("INVALID SQL")

    def test_ポーリングでタイムアウトすると例外を送出する(self):
        """ポーリングが最大回数に達した場合."""
        client = self._make_client()
        client._max_poll_attempts = 2
        client._poll_interval = 0

        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {
            "ret1": "Q12345",
            "msg1": "",
            "ret": "0",
            "msg": "",
        }

        # status=1 (処理中) が返り続ける
        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {
            "ret1": "1",
            "msg1": "",
            "ret": "0",
            "msg": "",
        }

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [submit_response, poll_response, poll_response]
            with pytest.raises(HrdbApiError, match="タイムアウト"):
                client.query("SELECT * FROM RACEMST")

    def test_CSV結果が0件の場合は空リストを返す(self):
        """結果が0件の場合."""
        client = self._make_client()

        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {
            "ret1": "Q12345",
            "msg1": "",
            "ret": "0",
            "msg": "",
        }

        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {
            "ret1": "2",
            "msg1": "",
            "ret": "0",
            "msg": "",
        }

        csv_response = MagicMock()
        csv_response.status_code = 200
        csv_response.text = ""

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [submit_response, poll_response, csv_response]
            result = client.query("SELECT * FROM RACEMST WHERE OPDT = '99991231'")

        assert result == []

    def test_ポーリングで処理失敗ステータスの場合は例外を送出する(self):
        """ポーリングでstatus=4(処理失敗)が返った場合."""
        client = self._make_client()

        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {
            "ret1": "Q12345",
            "msg1": "",
            "ret": "0",
            "msg": "",
        }

        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {
            "ret1": "4",
            "msg1": "Processing failed",
            "ret": "0",
            "msg": "",
        }

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [submit_response, poll_response]
            with pytest.raises(HrdbApiError, match="処理失敗"):
                client.query("SELECT * FROM RACEMST")

    def test_認証エラーで例外を送出する(self):
        """認証が失敗した場合."""
        client = self._make_client()

        error_response = MagicMock()
        error_response.status_code = 200
        error_response.json.return_value = {
            "ret": "-200",
            "msg": "Authentication failure.",
        }

        with patch("requests.post", return_value=error_response):
            with pytest.raises(HrdbApiError, match="Authentication failure"):
                client.query("SELECT * FROM RACEMST")
