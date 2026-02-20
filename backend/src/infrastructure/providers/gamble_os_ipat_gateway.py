"""GAMBLE-OS IPAT ゲートウェイ実装.

GAMBLE-OS API を直接呼び出して IPAT 投票・残高照会を行う。
"""
import json
import logging

import boto3
import requests

from src.domain.enums import IpatBetType
from src.domain.ports import IpatGateway, IpatGatewayError
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials

logger = logging.getLogger(__name__)

_BET_ENDPOINT = "https://api.gamble-os.net/systems/ip-bet-kb"
_BALANCE_ENDPOINT = "https://api.gamble-os.net/systems/ip-balance"
_REQUEST_TIMEOUT = 25

_BET_TYPE_CODE: dict[IpatBetType, str] = {
    IpatBetType.TANSYO: "TAN",
    IpatBetType.FUKUSYO: "FUKU",
    IpatBetType.UMAREN: "UMAFUKU",
    IpatBetType.WIDE: "WIDE",
    IpatBetType.UMATAN: "UMATAN",
    IpatBetType.SANRENPUKU: "SANFUKU",
    IpatBetType.SANRENTAN: "SANTAN",
}

_DEFAULT_SECRET_NAME = "baken-kaigi/gamble-os-credentials"


class GambleOsIpatGateway(IpatGateway):
    """GAMBLE-OS API 経由の IPAT ゲートウェイ."""

    def __init__(
        self,
        *,
        secrets_client: object | None = None,
        secret_name: str = _DEFAULT_SECRET_NAME,
        dry_run: bool = False,
    ) -> None:
        """初期化."""
        self._secrets_client = secrets_client or boto3.client("secretsmanager")
        self._secret_name = secret_name
        self._dry_run = dry_run
        self._cached_credentials: dict[str, str] | None = None

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def submit_bets(self, credentials: IpatCredentials, bet_lines: list[IpatBetLine]) -> bool:
        """投票を送信する."""
        gamble_os_creds = self._get_gamble_os_credentials()
        buyeye = self._build_buyeye(bet_lines)
        total_amount = sum(line.amount for line in bet_lines)

        payload = {
            "tncid": gamble_os_creds["tncid"],
            "tncpw": gamble_os_creds["tncpw"],
            "gov": "C",
            "uno": credentials.subscriber_number,
            "pin": credentials.pin,
            "pno": credentials.pars_number,
            "betcd": "betchk" if self._dry_run else "bet",
            "money": str(total_amount),
            "buyeye": buyeye,
        }

        try:
            response = requests.post(_BET_ENDPOINT, data=payload, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise IpatGatewayError(f"投票送信失敗: {e}") from e

        if data.get("ret", -1) < 0:
            raise IpatGatewayError(data.get("msg", "Unknown error"))

        return True

    def get_balance(self, credentials: IpatCredentials) -> IpatBalance:
        """残高を取得する."""
        gamble_os_creds = self._get_gamble_os_credentials()

        payload = {
            "tncid": gamble_os_creds["tncid"],
            "tncpw": gamble_os_creds["tncpw"],
            "gov": "C",
            "uno": credentials.subscriber_number,
            "pin": credentials.pin,
            "pno": credentials.pars_number,
        }

        try:
            response = requests.post(_BALANCE_ENDPOINT, data=payload, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise IpatGatewayError(f"残高照会失敗: {e}") from e

        if data.get("ret", -1) < 0:
            raise IpatGatewayError(data.get("msg", "Unknown error"))

        try:
            results = data["results"]
            day_buy_money = results["day_buy_money"]
            total_buy_money = results["total_buy_money"]
            buy_limit_money = results["buy_limit_money"]
        except KeyError as e:
            raise IpatGatewayError(f"残高照会レスポンスにフィールド欠損: {e}") from e

        return IpatBalance(
            bet_dedicated_balance=day_buy_money,
            settle_possible_balance=total_buy_money,
            bet_balance=buy_limit_money - day_buy_money,
            limit_vote_amount=buy_limit_money,
        )

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    def _get_gamble_os_credentials(self) -> dict[str, str]:
        """Secrets Manager から GAMBLE-OS 認証情報を取得（キャッシュ付き）."""
        if self._cached_credentials is not None:
            return self._cached_credentials

        response = self._secrets_client.get_secret_value(SecretId=self._secret_name)  # type: ignore[union-attr]
        secret = json.loads(response["SecretString"])
        self._cached_credentials = {"tncid": secret["tncid"], "tncpw": secret["tncpw"]}
        return self._cached_credentials

    @staticmethod
    def _build_buyeye(bet_lines: list[IpatBetLine]) -> str:
        """buyeye フォーマット文字列を構築する.

        フォーマット: 日付,レース場コード,レース番号,式別,方式,金額,買い目,マルチ
        各行を ":" で連結し、末尾も ":" で終わる。
        """
        parts: list[str] = []
        for line in bet_lines:
            bet_code = _BET_TYPE_CODE[line.bet_type]
            race_no = f"{line.race_number:02d}"
            entry = (
                f"{line.opdt},{line.venue_code.value},{race_no},"
                f"{bet_code},NORMAL,{line.amount},{line.number},"
            )
            parts.append(entry)
        return ":".join(parts) + ":"
