"""JraVanIpatGateway のテスト."""
import unittest
from unittest.mock import MagicMock, patch

from src.domain.enums import IpatBetType, IpatVenueCode
from src.domain.ports import IpatGatewayError
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
    def test_投票送信_競馬場コードが英語名で送信される(self, mock_session_cls: MagicMock) -> None:
        """ipatgo.exeはrcoursecdに英語名（TOKYO等）を期待する."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        self.gateway.submit_bets(self.credentials, self.bet_lines)

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert payload["bet_lines"][0]["rcoursecd"] == "TOKYO"

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
    def test_残高取得_レスポンスにフィールド不足でIpatGatewayError(
        self, mock_session_cls: MagicMock
    ) -> None:
        """APIが success:true を返すがbalanceフィールドが欠損した場合."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            # balance fields missing
        }
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(IpatGatewayError):
            self.gateway.get_balance(self.credentials)

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_残高取得_一部フィールド欠損でIpatGatewayError(
        self, mock_session_cls: MagicMock
    ) -> None:
        """一部のbalanceフィールドだけ返された場合."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "bet_dedicated_balance": 10000,
            # settle_possible_balance, bet_balance, limit_vote_amount missing
        }
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(IpatGatewayError):
            self.gateway.get_balance(self.credentials)

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_投票送信_競馬場コードが英語名で送信される(
        self, mock_session_cls: MagicMock
    ) -> None:
        """ipatgo.exeはrcoursecdに英語名（TOKYO等）を期待する."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        self.gateway.submit_bets(self.credentials, self.bet_lines)

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert payload["bet_lines"][0]["rcoursecd"] == "TOKYO"

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_投票送信_馬券式が大文字名で送信される(
        self, mock_session_cls: MagicMock
    ) -> None:
        """ipatgo.exeはdenominationに大文字名（TANSYO等）を期待する."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        self.gateway.submit_bets(self.credentials, self.bet_lines)

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert payload["bet_lines"][0]["denomination"] == "TANSYO"

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_投票送信_全券種が正しい形式で送信される(
        self, mock_session_cls: MagicMock
    ) -> None:
        """全券種のdenominationがipatgo.exe期待形式であること."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        for bet_type in IpatBetType:
            bet_line = IpatBetLine(
                opdt="20260207",
                venue_code=IpatVenueCode.TOKYO,
                race_number=11,
                bet_type=bet_type,
                number="01",
                amount=100,
            )
            self.gateway.submit_bets(self.credentials, [bet_line])
            call_args = mock_session.post.call_args
            denomination = call_args[1]["json"]["bet_lines"][0]["denomination"]
            assert denomination == bet_type.name, (
                f"{bet_type.name}: denomination '{denomination}' does not match enum name"
            )

    @patch("src.infrastructure.providers.jravan_ipat_gateway.requests.Session")
    def test_HTTPエラーで例外(self, mock_session_cls: MagicMock) -> None:
        import requests

        mock_session = MagicMock()
        mock_session.post.side_effect = requests.RequestException("Connection error")
        mock_session_cls.return_value = mock_session
        self.gateway._session = mock_session

        with self.assertRaises(Exception):
            self.gateway.submit_bets(self.credentials, self.bet_lines)
