"""JraVanIpatGateway のテスト."""
import unittest
from unittest.mock import MagicMock, patch

from src.domain.enums import IpatBetType, IpatVenueCode
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials
from src.infrastructure.providers.jravan_ipat_gateway import JraVanIpatGateway


class TestJraVanIpatGateway(unittest.TestCase):
    """JraVanIpatGateway のテスト."""

    def setUp(self) -> None:
        self.gateway = JraVanIpatGateway(base_url="http://test:8000")
        self.credentials = IpatCredentials(
            inet_id="ABcd1234",
            subscriber_number="12345678",
            pin="1234",
            pars_number="5678",
        )
        self.bet_lines = [
            IpatBetLine(
                opdt="20260207",
                venue_code=IpatVenueCode.TOKYO,
                race_number=11,
                bet_type=IpatBetType.TANSYO,
                number="01",
                amount=100,
            ),
        ]

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_投票送信_正常(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        result = self.gateway.submit_bets(self.credentials, self.bet_lines)
        assert result is True

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_投票送信_失敗(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": False, "error": "投票失敗"}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        result = self.gateway.submit_bets(self.credentials, self.bet_lines)
        assert result is False

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_残高取得_正常(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "bet_dedicated_balance": 10000,
            "settle_possible_balance": 50000,
            "bet_balance": 10000,
            "limit_vote_amount": 100000,
        }
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        result = self.gateway.get_balance(self.credentials)
        assert isinstance(result, IpatBalance)
        assert result.bet_balance == 10000

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_HTTPエラーで例外(self, mock_session_cls: MagicMock) -> None:
        import requests

        mock_session = MagicMock()
        mock_session.post.side_effect = requests.RequestException("Connection error")
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(Exception):
            self.gateway.submit_bets(self.credentials, self.bet_lines)
