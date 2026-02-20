"""GambleOsIpatGateway のテスト."""
import json
import unittest
from unittest.mock import MagicMock, patch

from src.domain.enums import IpatBetType, IpatVenueCode
from src.domain.ports import IpatGatewayError
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials
from src.infrastructure.providers.gamble_os_ipat_gateway import (
    GambleOsIpatGateway,
)


def _make_credentials() -> IpatCredentials:
    return IpatCredentials(
        inet_id="ABcd1234",
        subscriber_number="12345678",
        pin="1234",
        pars_number="5678",
    )


def _make_bet_line(
    *,
    bet_type: IpatBetType = IpatBetType.TANSYO,
    venue_code: IpatVenueCode = IpatVenueCode.TOKYO,
    race_number: int = 11,
    number: str = "01",
    amount: int = 100,
) -> IpatBetLine:
    return IpatBetLine(
        opdt="20260207",
        venue_code=venue_code,
        race_number=race_number,
        bet_type=bet_type,
        number=number,
        amount=amount,
    )


def _mock_secrets_manager(tncid: str = "testuser", tncpw: str = "testpass") -> MagicMock:
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"tncid": tncid, "tncpw": tncpw})
    }
    return mock_client


def _mock_response(*, status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


# ============================================================
# 投票テスト
# ============================================================
class TestGambleOsIpatGatewaySubmitBets(unittest.TestCase):
    """投票 submit_bets のテスト."""

    def setUp(self) -> None:
        self.sm_client = _mock_secrets_manager()
        self.credentials = _make_credentials()

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_投票正常系_ret0でTrue(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        result = gw.submit_bets(self.credentials, [_make_bet_line()])
        assert result is True

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_投票エラー_ret負でIpatGatewayError(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": -1, "msg": "認証エラー", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        with self.assertRaises(IpatGatewayError) as cm:
            gw.submit_bets(self.credentials, [_make_bet_line()])
        assert "認証エラー" in str(cm.exception)

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_buyeyeフォーマット_単勝(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        bet_line = _make_bet_line(
            bet_type=IpatBetType.TANSYO,
            venue_code=IpatVenueCode.TOKYO,
            race_number=11,
            number="01",
            amount=100,
        )
        gw.submit_bets(self.credentials, [bet_line])

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        buyeye = payload["buyeye"]
        # フォーマット: 日付,レース場コード,レース番号,式別,方式,金額,買い目,マルチ
        assert buyeye == "20260207,05,11,TAN,NORMAL,100,01,:"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_buyeyeフォーマット_三連単(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        bet_line = _make_bet_line(
            bet_type=IpatBetType.SANRENTAN,
            venue_code=IpatVenueCode.HANSHIN,
            race_number=1,
            number="01-02-03",
            amount=500,
        )
        gw.submit_bets(self.credentials, [bet_line])

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        buyeye = payload["buyeye"]
        assert buyeye == "20260207,09,01,SANTAN,NORMAL,500,01-02-03,:"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_複数買い目の連結(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        lines = [
            _make_bet_line(bet_type=IpatBetType.TANSYO, number="01", amount=100),
            _make_bet_line(bet_type=IpatBetType.FUKUSYO, number="03", amount=200),
        ]
        gw.submit_bets(self.credentials, lines)

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        buyeye = payload["buyeye"]
        parts = buyeye.split(":")
        # 最後の ":" で終わるため、末尾は空文字列
        assert len(parts) == 3  # 2買い目 + 末尾空文字列
        assert parts[0] == "20260207,05,11,TAN,NORMAL,100,01,"
        assert parts[1] == "20260207,05,11,FUKU,NORMAL,200,03,"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_IPAT認証情報マッピング(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        gw.submit_bets(self.credentials, [_make_bet_line()])

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        assert payload["uno"] == "12345678"  # subscriber_number
        assert payload["pin"] == "1234"
        assert payload["pno"] == "5678"  # pars_number

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_ドライランモード(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client, dry_run=True)
        gw.submit_bets(self.credentials, [_make_bet_line()])

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        assert payload["betcd"] == "betchk"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_通常モードのbetcd(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client, dry_run=False)
        gw.submit_bets(self.credentials, [_make_bet_line()])

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        assert payload["betcd"] == "bet"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_HTTPエラーでIpatGatewayError(self, mock_requests: MagicMock) -> None:
        import requests as req_lib

        mock_requests.post.side_effect = req_lib.RequestException("Connection refused")
        mock_requests.RequestException = req_lib.RequestException
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        with self.assertRaises(IpatGatewayError):
            gw.submit_bets(self.credentials, [_make_bet_line()])

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_全7券種のコード変換(self, mock_requests: MagicMock) -> None:
        expected_mapping = {
            IpatBetType.TANSYO: "TAN",
            IpatBetType.FUKUSYO: "FUKU",
            IpatBetType.UMAREN: "UMAFUKU",
            IpatBetType.WIDE: "WIDE",
            IpatBetType.UMATAN: "UMATAN",
            IpatBetType.SANRENPUKU: "SANFUKU",
            IpatBetType.SANRENTAN: "SANTAN",
        }
        for bet_type, expected_code in expected_mapping.items():
            mock_requests.post.return_value = _mock_response(
                json_data={"ret": 0, "msg": "", "results": {}}
            )
            gw = GambleOsIpatGateway(secrets_client=self.sm_client)
            gw.submit_bets(self.credentials, [_make_bet_line(bet_type=bet_type)])

            call_args = mock_requests.post.call_args
            payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
            buyeye = payload["buyeye"]
            actual_code = buyeye.split(",")[3]
            assert actual_code == expected_code, (
                f"{bet_type.name}: expected '{expected_code}', got '{actual_code}'"
            )

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_投票合計金額がmoneyフィールドに設定される(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        lines = [
            _make_bet_line(amount=100),
            _make_bet_line(amount=300),
        ]
        gw.submit_bets(self.credentials, lines)

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        assert payload["money"] == "400"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_投票エンドポイントURL(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        gw.submit_bets(self.credentials, [_make_bet_line()])

        call_args = mock_requests.post.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url")
        assert url == "https://api.gamble-os.net/systems/ip-bet-kb"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_GAMBLE_OS認証情報がペイロードに含まれる(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        sm = _mock_secrets_manager(tncid="myid", tncpw="mypw")
        gw = GambleOsIpatGateway(secrets_client=sm)
        gw.submit_bets(self.credentials, [_make_bet_line()])

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        assert payload["tncid"] == "myid"
        assert payload["tncpw"] == "mypw"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_govフィールドがCである(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        gw.submit_bets(self.credentials, [_make_bet_line()])

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        assert payload["gov"] == "C"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_レース番号が2桁0埋めでbuyeyeに含まれる(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        bet_line = _make_bet_line(race_number=1)
        gw.submit_bets(self.credentials, [bet_line])

        call_args = mock_requests.post.call_args
        payload = call_args[1]["data"] if "data" in call_args[1] else call_args[1].get("json")
        buyeye = payload["buyeye"]
        race_no_part = buyeye.split(",")[2]
        assert race_no_part == "01"


# ============================================================
# 残高照会テスト
# ============================================================
class TestGambleOsIpatGatewayGetBalance(unittest.TestCase):
    """残高照会 get_balance のテスト."""

    def setUp(self) -> None:
        self.sm_client = _mock_secrets_manager()
        self.credentials = _make_credentials()

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_残高取得正常系_フィールドマッピング(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={
                "ret": 0,
                "msg": "",
                "results": {
                    "day_buy_money": 5000,
                    "total_buy_money": 30000,
                    "buy_limit_money": 100000,
                },
            }
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        balance = gw.get_balance(self.credentials)

        assert isinstance(balance, IpatBalance)
        assert balance.bet_dedicated_balance == 5000  # day_buy_money
        assert balance.settle_possible_balance == 30000  # total_buy_money
        assert balance.limit_vote_amount == 100000  # buy_limit_money
        assert balance.bet_balance == 95000  # buy_limit_money - day_buy_money

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_残高取得エラー_ret負でIpatGatewayError(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": -1, "msg": "セッション切れ", "results": {}}
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        with self.assertRaises(IpatGatewayError) as cm:
            gw.get_balance(self.credentials)
        assert "セッション切れ" in str(cm.exception)

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_残高取得_フィールド欠損でIpatGatewayError(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={
                "ret": 0,
                "msg": "",
                "results": {
                    "day_buy_money": 5000,
                    # total_buy_money, buy_limit_money 欠損
                },
            }
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        with self.assertRaises(IpatGatewayError):
            gw.get_balance(self.credentials)

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_残高照会エンドポイントURL(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={
                "ret": 0,
                "msg": "",
                "results": {
                    "day_buy_money": 0,
                    "total_buy_money": 0,
                    "buy_limit_money": 100000,
                },
            }
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        gw.get_balance(self.credentials)

        call_args = mock_requests.post.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url")
        assert url == "https://api.gamble-os.net/systems/ip-balance"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_残高照会_HTTPエラーでIpatGatewayError(self, mock_requests: MagicMock) -> None:
        import requests as req_lib

        mock_requests.post.side_effect = req_lib.RequestException("Timeout")
        mock_requests.RequestException = req_lib.RequestException
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        with self.assertRaises(IpatGatewayError):
            gw.get_balance(self.credentials)

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_残高照会_results欠損でIpatGatewayError(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": ""}
            # results キー自体が欠損
        )
        gw = GambleOsIpatGateway(secrets_client=self.sm_client)
        with self.assertRaises(IpatGatewayError):
            gw.get_balance(self.credentials)


# ============================================================
# Secrets Manager キャッシュテスト
# ============================================================
class TestGambleOsIpatGatewaySecretsCache(unittest.TestCase):
    """Secrets Manager 認証情報キャッシュのテスト."""

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests")
    def test_認証情報はキャッシュされ2回目はSecretsManagerを呼ばない(
        self, mock_requests: MagicMock
    ) -> None:
        mock_requests.post.return_value = _mock_response(
            json_data={"ret": 0, "msg": "", "results": {}}
        )
        sm_client = _mock_secrets_manager()
        gw = GambleOsIpatGateway(secrets_client=sm_client)
        creds = _make_credentials()

        gw.submit_bets(creds, [_make_bet_line()])
        gw.submit_bets(creds, [_make_bet_line()])

        # get_secret_value は1回だけ呼ばれる
        assert sm_client.get_secret_value.call_count == 1
