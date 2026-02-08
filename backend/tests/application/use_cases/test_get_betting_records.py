"""GetBettingRecordsUseCase のテスト."""
from datetime import date

from src.application.use_cases.get_betting_records import GetBettingRecordsUseCase
from src.domain.entities import BettingRecord
from src.domain.enums import BetType
from src.domain.identifiers import RaceId, UserId
from src.domain.value_objects import HorseNumbers, Money
from src.infrastructure.repositories.in_memory_betting_record_repository import (
    InMemoryBettingRecordRepository,
)


def _make_record(
    user_id: str = "user-001",
    race_date: date = date(2026, 5, 5),
    venue: str = "東京",
    bet_type: BetType = BetType.WIN,
) -> BettingRecord:
    return BettingRecord.create(
        user_id=UserId(user_id),
        race_id=RaceId("202605051211"),
        race_name="東京11R",
        race_date=race_date,
        venue=venue,
        bet_type=bet_type,
        horse_numbers=HorseNumbers.of(1),
        amount=Money.of(100),
    )


class TestGetBettingRecordsUseCase:
    """GetBettingRecordsUseCase のテスト."""

    def test_ユーザーの投票記録を取得できる(self) -> None:
        repo = InMemoryBettingRecordRepository()
        repo.save(_make_record())
        repo.save(_make_record())
        use_case = GetBettingRecordsUseCase(betting_record_repository=repo)

        results = use_case.execute(user_id="user-001")
        assert len(results) == 2

    def test_他ユーザーの記録は含まれない(self) -> None:
        repo = InMemoryBettingRecordRepository()
        repo.save(_make_record(user_id="user-001"))
        repo.save(_make_record(user_id="user-002"))
        use_case = GetBettingRecordsUseCase(betting_record_repository=repo)

        results = use_case.execute(user_id="user-001")
        assert len(results) == 1

    def test_記録なしで空リスト(self) -> None:
        repo = InMemoryBettingRecordRepository()
        use_case = GetBettingRecordsUseCase(betting_record_repository=repo)

        results = use_case.execute(user_id="user-001")
        assert results == []

    def test_日付フィルタで絞り込める(self) -> None:
        repo = InMemoryBettingRecordRepository()
        repo.save(_make_record(race_date=date(2026, 5, 1)))
        repo.save(_make_record(race_date=date(2026, 5, 10)))
        repo.save(_make_record(race_date=date(2026, 5, 20)))
        use_case = GetBettingRecordsUseCase(betting_record_repository=repo)

        results = use_case.execute(
            user_id="user-001",
            date_from="2026-05-05",
            date_to="2026-05-15",
        )
        assert len(results) == 1

    def test_開催場フィルタで絞り込める(self) -> None:
        repo = InMemoryBettingRecordRepository()
        repo.save(_make_record(venue="東京"))
        repo.save(_make_record(venue="中山"))
        use_case = GetBettingRecordsUseCase(betting_record_repository=repo)

        results = use_case.execute(user_id="user-001", venue="東京")
        assert len(results) == 1
        assert results[0].venue == "東京"

    def test_券種フィルタで絞り込める(self) -> None:
        repo = InMemoryBettingRecordRepository()
        repo.save(_make_record(bet_type=BetType.WIN))
        repo.save(_make_record(bet_type=BetType.TRIFECTA))
        use_case = GetBettingRecordsUseCase(betting_record_repository=repo)

        results = use_case.execute(user_id="user-001", bet_type="win")
        assert len(results) == 1
        assert results[0].bet_type == BetType.WIN
