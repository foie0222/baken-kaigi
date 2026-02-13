"""IPATエンドポイントのテスト."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# テスト対象モジュールへのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# database モジュールをモック
sys.modules["database"] = MagicMock()
sys.modules["jra_checksum_scraper"] = MagicMock()

from main import app

client = TestClient(app)


class TestIpatVoteEndpoint:
    """POST /ipat/vote エンドポイントのテスト."""

    @patch("main.IpatExecutor")
    def test_投票成功(self, mock_executor_class: MagicMock) -> None:
        """正常な投票リクエストで200が返ることを確認."""
        mock_instance = MagicMock()
        mock_instance.vote.return_value = {"success": True}
        mock_executor_class.return_value = mock_instance

        response = client.post("/ipat/vote", json={
            "inet_id": "ABcd1234",
            "subscriber_number": "12345678",
            "pin": "1234",
            "pars_number": "5678",
            "bet_lines": [
                {
                    "opdt": "20260201",
                    "rcoursecd": "05",
                    "rno": "11",
                    "denomination": "tansyo",
                    "method": "NORMAL",
                    "multi": "",
                    "number": "03",
                    "bet_price": "100",
                },
            ],
        })

        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("main.IpatExecutor")
    def test_投票失敗(self, mock_executor_class: MagicMock) -> None:
        """投票失敗時にsuccessがfalseで返ることを確認."""
        mock_instance = MagicMock()
        mock_instance.vote.return_value = {"success": False, "message": "IPAT通信エラー"}
        mock_executor_class.return_value = mock_instance

        response = client.post("/ipat/vote", json={
            "inet_id": "ABcd1234",
            "subscriber_number": "12345678",
            "pin": "1234",
            "pars_number": "5678",
            "bet_lines": [
                {
                    "opdt": "20260201",
                    "rcoursecd": "05",
                    "rno": "11",
                    "denomination": "tansyo",
                    "method": "NORMAL",
                    "multi": "",
                    "number": "03",
                    "bet_price": "100",
                },
            ],
        })

        assert response.status_code == 200
        assert response.json()["success"] is False


class TestIpatStatEndpoint:
    """POST /ipat/stat エンドポイントのテスト."""

    @patch("main.IpatExecutor")
    def test_残高取得成功(self, mock_executor_class: MagicMock) -> None:
        """正常な残高取得リクエストで200が返ることを確認."""
        mock_instance = MagicMock()
        mock_instance.stat.return_value = {
            "success": True,
            "bet_dedicated_balance": 10000,
            "settle_possible_balance": 5000,
            "bet_balance": 15000,
            "limit_vote_amount": 100000,
        }
        mock_executor_class.return_value = mock_instance

        response = client.post("/ipat/stat", json={
            "inet_id": "ABcd1234",
            "subscriber_number": "12345678",
            "pin": "1234",
            "pars_number": "5678",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["bet_balance"] == 15000

    @patch("main.IpatExecutor")
    def test_残高取得失敗(self, mock_executor_class: MagicMock) -> None:
        """残高取得失敗時にsuccessがfalseで返ることを確認."""
        mock_instance = MagicMock()
        mock_instance.stat.return_value = {"success": False, "message": "IPAT通信エラー"}
        mock_executor_class.return_value = mock_instance

        response = client.post("/ipat/stat", json={
            "inet_id": "ABcd1234",
            "subscriber_number": "12345678",
            "pin": "1234",
            "pars_number": "5678",
        })

        assert response.status_code == 200
        assert response.json()["success"] is False
