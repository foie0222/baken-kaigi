"""JRAチェックサム更新Lambdaのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.jra_checksum_updater import handler, MAX_RETRIES


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch.dict("os.environ", {"JRAVAN_API_URL": "http://10.0.1.100:8000"})
    @patch("batch.jra_checksum_updater.requests")
    def test_正常終了時は200を返す(self, mock_requests):
        """正常系: API呼び出し成功時はstatusCode 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "target_date": "20260207",
            "total_venues": 3,
            "saved_count": 3,
        }
        mock_requests.post.return_value = mock_response

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    @patch.dict("os.environ", {"JRAVAN_API_URL": "http://10.0.1.100:8000"})
    @patch("batch.jra_checksum_updater.requests")
    def test_API呼び出し失敗時は500を返す(self, mock_requests):
        """異常系: API呼び出し失敗（非接続エラー）時はstatusCode 500."""
        import requests as real_requests
        mock_requests.post.side_effect = real_requests.RequestException("Bad request")
        mock_requests.RequestException = real_requests.RequestException
        mock_requests.ConnectionError = real_requests.ConnectionError

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False

    @patch.dict("os.environ", {}, clear=True)
    def test_環境変数未設定時は500を返す(self):
        """異常系: JRAVAN_API_URL未設定時はstatusCode 500."""
        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False
        assert "JRAVAN_API_URL" in result["body"]["error"]

    @patch.dict("os.environ", {"JRAVAN_API_URL": "http://10.0.1.100:8000"})
    @patch("batch.jra_checksum_updater.time.sleep")
    @patch("batch.jra_checksum_updater.requests")
    def test_接続エラー時にリトライして成功(self, mock_requests, mock_sleep):
        """正常系: 接続エラー後のリトライで成功."""
        import requests as real_requests
        mock_requests.ConnectionError = real_requests.ConnectionError
        mock_requests.RequestException = real_requests.RequestException

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        # 1回目: 接続エラー、2回目: 成功
        mock_requests.post.side_effect = [
            real_requests.ConnectionError("Connection refused"),
            mock_response,
        ]

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True
        assert mock_requests.post.call_count == 2
        mock_sleep.assert_called_once()

    @patch.dict("os.environ", {"JRAVAN_API_URL": "http://10.0.1.100:8000"})
    @patch("batch.jra_checksum_updater.time.sleep")
    @patch("batch.jra_checksum_updater.requests")
    def test_接続エラーが全リトライで失敗(self, mock_requests, mock_sleep):
        """異常系: 全リトライが接続エラーで失敗."""
        import requests as real_requests
        mock_requests.ConnectionError = real_requests.ConnectionError
        mock_requests.RequestException = real_requests.RequestException

        mock_requests.post.side_effect = real_requests.ConnectionError("Connection refused")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False
        assert "retries" in result["body"]["error"]
        assert mock_requests.post.call_count == MAX_RETRIES
        assert mock_sleep.call_count == MAX_RETRIES - 1
