"""GambleOsIpatGateway のテスト."""
import unittest
from unittest.mock import MagicMock, patch

import requests

from src.domain.enums import IpatBetType, IpatVenueCode
from src.domain.ports import IpatGatewayError
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials
from src.infrastructure.providers.gambleos_ipat_gateway import GambleOsIpatGateway


class TestGambleOsIpatGateway(unittest.TestCase):
    """GambleOsIpatGateway のテスト."""

    def setUp(self) -> None:
        self.gateway = GambleOsIpatGateway(base_url="https://api.gamble-os.net")
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

    @patch("src.infrastructure.providers.gambleos_ipat_gateway.requests.Session")
    def test_投票送信_正常(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": "0", "msg": "", "results": []}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        result = self.gateway.submit_bets(self.credentials, self.bet_lines)
        assert result is True

        call_args = mock_session.post.call_args
        assert "/systems/ip-bet-kb" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["tncid"] == "ABcd1234"
        assert payload["tncpw"] == "1234"
        assert len(payload["bet_lines"]) == 1
        bet = payload["bet_lines"][0]
        assert bet["opdt"] == "20260207"
        assert bet["rno"] == "11"
        assert bet["bet_price"] == "100"

    @patch("src.infrastructure.providers.gambleos_ipat_gateway.requests.Session")
    def test_投票送信_APIエラー(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ret": "1",
            "msg": "投票受付時間外です",
            "results": [],
        }
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(IpatGatewayError) as ctx:
            self.gateway.submit_bets(self.credentials, self.bet_lines)
        assert "投票受付時間外です" in str(ctx.exception)

    @patch("src.infrastructure.providers.gambleos_ipat_gateway.requests.Session")
    def test_投票送信_ネットワークエラー(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.post.side_effect = requests.ConnectionError("Connection refused")
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(IpatGatewayError):
            self.gateway.submit_bets(self.credentials, self.bet_lines)

    @patch("src.infrastructure.providers.gambleos_ipat_gateway.requests.Session")
    def test_残高照会_正常(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ret": "0",
            "msg": "",
            "results": [
                {
                    "bet_dedicated_balance": 10000,
                    "settle_possible_balance": 50000,
                    "bet_balance": 10000,
                    "limit_vote_amount": 100000,
                }
            ],
        }
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        result = self.gateway.get_balance(self.credentials)
        assert isinstance(result, IpatBalance)
        assert result.bet_dedicated_balance == 10000
        assert result.settle_possible_balance == 50000
        assert result.bet_balance == 10000
        assert result.limit_vote_amount == 100000

        call_args = mock_session.post.call_args
        assert "/systems/ip-balance" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["tncid"] == "ABcd1234"
        assert payload["tncpw"] == "1234"
        assert payload["inet_id"] == "ABcd1234"
        assert payload["subscriber_no"] == "12345678"
        assert payload["pin"] == "1234"
        assert payload["pars_no"] == "5678"

    @patch("src.infrastructure.providers.gambleos_ipat_gateway.requests.Session")
    def test_残高照会_APIエラー(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ret": "2",
            "msg": "認証エラー",
            "results": [],
        }
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(IpatGatewayError) as ctx:
            self.gateway.get_balance(self.credentials)
        assert "認証エラー" in str(ctx.exception)

    @patch("src.infrastructure.providers.gambleos_ipat_gateway.requests.Session")
    def test_残高照会_ネットワークエラー(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.post.side_effect = requests.Timeout("Request timed out")
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(IpatGatewayError):
            self.gateway.get_balance(self.credentials)

    @patch("src.infrastructure.providers.gambleos_ipat_gateway.requests.Session")
    def test_残高照会_レスポンスにresultsが空でエラー(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": "0", "msg": "", "results": []}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(IpatGatewayError):
            self.gateway.get_balance(self.credentials)

    @patch("src.infrastructure.providers.gambleos_ipat_gateway.requests.Session")
    def test_複数買い目の投票送信(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": "0", "msg": "", "results": []}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        bet_lines = [
            IpatBetLine(
                opdt="20260207",
                venue_code=IpatVenueCode.TOKYO,
                race_number=11,
                bet_type=IpatBetType.TANSYO,
                number="01",
                amount=100,
            ),
            IpatBetLine(
                opdt="20260207",
                venue_code=IpatVenueCode.TOKYO,
                race_number=11,
                bet_type=IpatBetType.TANSYO,
                number="05",
                amount=200,
            ),
        ]

        result = self.gateway.submit_bets(self.credentials, bet_lines)
        assert result is True

        payload = mock_session.post.call_args[1]["json"]
        assert len(payload["bet_lines"]) == 2

    def test_環境変数でベースURL設定(self) -> None:
        import os

        with patch.dict(os.environ, {"GAMBLEOS_API_URL": "https://custom.example.com"}):
            gw = GambleOsIpatGateway()
            assert gw._base_url == "https://custom.example.com"

    def test_デフォルトベースURL(self) -> None:
        import os

        with patch.dict(os.environ, {}, clear=True):
            env_backup = os.environ.pop("GAMBLEOS_API_URL", None)
            try:
                gw = GambleOsIpatGateway()
                assert gw._base_url == "https://api.gamble-os.net"
            finally:
                if env_backup is not None:
                    os.environ["GAMBLEOS_API_URL"] = env_backup
