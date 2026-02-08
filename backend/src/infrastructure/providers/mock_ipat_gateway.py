"""IPATゲートウェイのモック実装."""
from src.domain.ports import IpatGateway
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials


class MockIpatGateway(IpatGateway):
    """IPATゲートウェイのモック実装（テスト用、エラー設定可能）."""

    def __init__(self) -> None:
        """初期化."""
        self._balance_error: Exception | None = None
        self._submit_error: Exception | None = None

    def set_balance_error(self, error: Exception) -> None:
        """残高照会時にエラーを発生させる設定."""
        self._balance_error = error

    def set_submit_error(self, error: Exception) -> None:
        """投票送信時にエラーを発生させる設定."""
        self._submit_error = error

    def submit_bets(self, credentials: IpatCredentials, bet_lines: list[IpatBetLine]) -> bool:
        """投票を送信する（エラー設定時は例外送出）."""
        if self._submit_error:
            raise self._submit_error
        return True

    def get_balance(self, credentials: IpatCredentials) -> IpatBalance:
        """残高を取得する（エラー設定時は例外送出）."""
        if self._balance_error:
            raise self._balance_error
        return IpatBalance(
            bet_dedicated_balance=100000,
            settle_possible_balance=100000,
            bet_balance=100000,
            limit_vote_amount=1000000,
        )
