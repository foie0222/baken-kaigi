"""IPATゲートウェイのモック実装."""
from src.domain.ports import IpatGateway
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials


class MockIpatGateway(IpatGateway):
    """IPATゲートウェイのモック実装（テスト用、常に成功）."""

    def submit_bets(self, credentials: IpatCredentials, bet_lines: list[IpatBetLine]) -> bool:
        """投票を送信する（常に成功）."""
        return True

    def get_balance(self, credentials: IpatCredentials) -> IpatBalance:
        """残高を取得する（固定値を返す）."""
        return IpatBalance(
            bet_dedicated_balance=100000,
            settle_possible_balance=100000,
            bet_balance=100000,
            limit_vote_amount=1000000,
        )
