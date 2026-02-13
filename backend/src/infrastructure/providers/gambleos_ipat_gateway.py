"""GAMBLE-OS IPAT ゲートウェイ実装.

GAMBLE-OS JRA-IPAT投票APIを経由して投票・残高照会を行う。
"""
import logging
import os

import requests
from requests.adapters import HTTPAdapter

from src.domain.ports import IpatGateway, IpatGatewayError
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials

logger = logging.getLogger(__name__)


class GambleOsIpatGateway(IpatGateway):
    """GAMBLE-OS API 経由の IPAT ゲートウェイ."""

    DEFAULT_TIMEOUT = 10

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self._base_url = base_url or os.environ.get(
            "GAMBLEOS_API_URL", "https://api.gamble-os.net"
        )
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """HTTP セッションを作成する.

        投票の重複実行リスクがあるためリトライは行わない。
        """
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=0)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def submit_bets(self, credentials: IpatCredentials, bet_lines: list[IpatBetLine]) -> bool:
        """投票を送信する."""
        try:
            bet_line_dicts = [
                {
                    "opdt": line.opdt,
                    "rcoursecd": line.venue_code.value,
                    "rno": f"{line.race_number:02d}",
                    "denomination": line.bet_type.value,
                    "method": "NORMAL",
                    "multi": "",
                    "number": line.number,
                    "bet_price": str(line.amount),
                }
                for line in bet_lines
            ]
            payload = {
                "tncid": credentials.inet_id,
                "tncpw": credentials.pin,
                "bet_lines": bet_line_dicts,
            }
            response = self._session.post(
                f"{self._base_url}/systems/ip-bet-kb",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("ret") != "0":
                raise IpatGatewayError(
                    f"Failed to submit bets: {data.get('msg', 'Unknown error')}"
                )
            return True
        except requests.RequestException as e:
            raise IpatGatewayError(f"Failed to submit bets: {e}") from e

    def get_balance(self, credentials: IpatCredentials) -> IpatBalance:
        """残高を取得する."""
        try:
            payload = {
                "tncid": credentials.inet_id,
                "tncpw": credentials.pin,
                "inet_id": credentials.inet_id,
                "subscriber_no": credentials.subscriber_number,
                "pin": credentials.pin,
                "pars_no": credentials.pars_number,
            }
            response = self._session.post(
                f"{self._base_url}/systems/ip-balance",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("ret") != "0":
                raise IpatGatewayError(
                    f"Failed to get balance: {data.get('msg', 'Unknown error')}"
                )
            results = data.get("results", [])
            if not results:
                raise IpatGatewayError("Failed to get balance: empty results")
            balance_data = results[0]
            return IpatBalance(
                bet_dedicated_balance=balance_data["bet_dedicated_balance"],
                settle_possible_balance=balance_data["settle_possible_balance"],
                bet_balance=balance_data["bet_balance"],
                limit_vote_amount=balance_data["limit_vote_amount"],
            )
        except requests.RequestException as e:
            raise IpatGatewayError(f"Failed to get balance: {e}") from e
        except KeyError as e:
            raise IpatGatewayError(
                f"Failed to get balance: missing field {e} in response"
            ) from e
