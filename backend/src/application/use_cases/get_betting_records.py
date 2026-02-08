"""投票記録取得ユースケース."""
from datetime import date
from typing import Optional

from src.domain.entities import BettingRecord
from src.domain.enums import BetType
from src.domain.identifiers import UserId
from src.domain.ports import BettingRecordRepository


class GetBettingRecordsUseCase:
    """投票記録取得ユースケース."""

    def __init__(self, betting_record_repository: BettingRecordRepository) -> None:
        """初期化."""
        self._betting_record_repository = betting_record_repository

    def execute(
        self,
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        venue: Optional[str] = None,
        bet_type: Optional[str] = None,
    ) -> list[BettingRecord]:
        """投票記録を取得する."""
        from_date = date.fromisoformat(date_from) if date_from else None
        to_date = date.fromisoformat(date_to) if date_to else None
        bt = BetType(bet_type) if bet_type else None

        return self._betting_record_repository.find_by_user_id(
            user_id=UserId(user_id),
            from_date=from_date,
            to_date=to_date,
            venue=venue,
            bet_type=bt,
        )
