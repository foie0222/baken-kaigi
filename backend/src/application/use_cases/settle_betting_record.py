"""投票記録確定ユースケース."""
from src.domain.entities import BettingRecord
from src.domain.identifiers import BettingRecordId, UserId
from src.domain.ports import BettingRecordRepository
from src.domain.value_objects import Money


class BettingRecordNotFoundError(Exception):
    """投票記録が見つからないエラー."""

    pass


class SettleBettingRecordUseCase:
    """投票記録確定ユースケース."""

    def __init__(self, betting_record_repository: BettingRecordRepository) -> None:
        """初期化."""
        self._betting_record_repository = betting_record_repository

    def execute(self, user_id: str, record_id: str, payout: int) -> BettingRecord:
        """投票記録を確定する."""
        record = self._betting_record_repository.find_by_id(BettingRecordId(record_id))

        if record is None or record.user_id != UserId(user_id):
            raise BettingRecordNotFoundError(f"Betting record not found: {record_id}")

        record.settle(Money.of(payout))
        self._betting_record_repository.save(record)
        return record
