"""IPATゲートウェイインターフェース."""
from abc import ABC, abstractmethod

from ..value_objects import IpatBalance, IpatBetLine, IpatCredentials


class IpatGatewayError(Exception):
    """IPAT ゲートウェイエラー."""

    pass


class IpatGateway(ABC):
    """IPAT投票ゲートウェイのインターフェース."""

    @abstractmethod
    def submit_bets(self, credentials: IpatCredentials, bet_lines: list[IpatBetLine]) -> bool:
        """投票を送信する."""
        pass

    @abstractmethod
    def get_balance(self, credentials: IpatCredentials) -> IpatBalance:
        """残高を取得する."""
        pass
