"""JRAチェックサム更新Lambdaのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.jra_checksum_updater import handler


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
        """異常系: API呼び出し失敗時はstatusCode 500."""
        import requests as real_requests
        mock_requests.post.side_effect = real_requests.RequestException("Connection refused")
        mock_requests.RequestException = real_requests.RequestException

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
