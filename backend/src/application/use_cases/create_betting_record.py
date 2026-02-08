"""投票記録作成ユースケース."""
from datetime import date

from src.domain.entities import BettingRecord
from src.domain.enums import BetType
from src.domain.identifiers import RaceId, UserId
from src.domain.ports import BettingRecordRepository
from src.domain.value_objects import HorseNumbers, Money


class CreateBettingRecordUseCase:
    """投票記録作成ユースケース."""

    def __init__(self, betting_record_repository: BettingRecordRepository) -> None:
        """初期化."""
        self._betting_record_repository = betting_record_repository

    def execute(
        self,
        user_id: str,
        race_id: str,
        race_name: str,
        race_date: str,
        venue: str,
        bet_type: str,
        horse_numbers: list[int],
        amount: int,
    ) -> BettingRecord:
        """投票記録を作成する."""
        record = BettingRecord.create(
            user_id=UserId(user_id),
            race_id=RaceId(race_id),
            race_name=race_name,
            race_date=date.fromisoformat(race_date),
            venue=venue,
            bet_type=BetType(bet_type),
            horse_numbers=HorseNumbers.from_list(horse_numbers),
            amount=Money.of(amount),
        )
        self._betting_record_repository.save(record)
        return record
