"""JRA-VAN IPAT ゲートウェイ実装.

EC2 Windows 上の jravan-api 経由で IPAT 投票・残高照会を行う。
"""
import logging
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.domain.ports import IpatGateway
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials

logger = logging.getLogger(__name__)


class JraVanIpatGateway(IpatGateway):
    """JRA-VAN jravan-api 経由の IPAT ゲートウェイ."""

    DEFAULT_TIMEOUT = 30

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        """初期化."""
        self._base_url = base_url or os.environ.get(
            "JRAVAN_API_URL", "http://10.0.1.100:8000"
        )
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """リトライ機能付きの HTTP セッションを作成する."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def submit_bets(self, credentials: IpatCredentials, bet_lines: list[IpatBetLine]) -> bool:
        """投票を送信する."""
        try:
            csv_lines = [line.to_csv_line() for line in bet_lines]
            payload = {
                "card_number": credentials.card_number,
                "birthday": credentials.birthday,
                "pin": credentials.pin,
                "dummy_pin": credentials.dummy_pin,
                "bet_lines": csv_lines,
            }
            response = self._session.post(
                f"{self._base_url}/ipat/vote",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("success", False)
        except requests.RequestException as e:
            logger.error(f"Failed to submit bets: {e}")
            raise IpatGatewayError(f"Failed to submit bets: {e}") from e

    def get_balance(self, credentials: IpatCredentials) -> IpatBalance:
        """残高を取得する."""
        try:
            payload = {
                "card_number": credentials.card_number,
                "birthday": credentials.birthday,
                "pin": credentials.pin,
                "dummy_pin": credentials.dummy_pin,
            }
            response = self._session.post(
                f"{self._base_url}/ipat/stat",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return IpatBalance(
                bet_dedicated_balance=data["bet_dedicated_balance"],
                settle_possible_balance=data["settle_possible_balance"],
                bet_balance=data["bet_balance"],
                limit_vote_amount=data["limit_vote_amount"],
            )
        except requests.RequestException as e:
            logger.error(f"Failed to get balance: {e}")
            raise IpatGatewayError(f"Failed to get balance: {e}") from e


class IpatGatewayError(Exception):
    """IPAT ゲートウェイエラー."""

    pass
