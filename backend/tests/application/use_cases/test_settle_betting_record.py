"""SettleBettingRecordUseCase のテスト."""
from datetime import date

import pytest

from src.application.use_cases.settle_betting_record import (
    BettingRecordNotFoundError,
    SettleBettingRecordUseCase,
)
from src.domain.entities import BettingRecord
from src.domain.enums import BetType, BettingRecordStatus
from src.domain.identifiers import RaceId, UserId
from src.domain.value_objects import HorseNumbers, Money
from src.infrastructure.repositories.in_memory_betting_record_repository import (
    InMemoryBettingRecordRepository,
)


def _make_record(user_id: str = "user-001") -> BettingRecord:
    return BettingRecord.create(
        user_id=UserId(user_id),
        race_id=RaceId("202605051211"),
        race_name="東京11R",
        race_date=date(2026, 5, 5),
        venue="東京",
        bet_type=BetType.WIN,
        horse_numbers=HorseNumbers.of(1),
        amount=Money.of(100),
    )


class TestSettleBettingRecordUseCase:
    """SettleBettingRecordUseCase のテスト."""

    def test_投票記録を確定できる(self) -> None:
        repo = InMemoryBettingRecordRepository()
        record = _make_record()
        repo.save(record)
        use_case = SettleBettingRecordUseCase(betting_record_repository=repo)

        settled = use_case.execute(
            user_id="user-001",
            record_id=record.record_id.value,
            payout=500,
        )

        assert settled.status == BettingRecordStatus.SETTLED
        assert settled.payout.value == 500
        assert settled.profit.value == 400

    def test_ハズレの場合利益ゼロ(self) -> None:
        repo = InMemoryBettingRecordRepository()
        record = _make_record()
        repo.save(record)
        use_case = SettleBettingRecordUseCase(betting_record_repository=repo)

        settled = use_case.execute(
            user_id="user-001",
            record_id=record.record_id.value,
            payout=0,
        )

        assert settled.status == BettingRecordStatus.SETTLED
        assert settled.payout.value == 0
        assert settled.profit.value == 0

    def test_存在しない記録でエラー(self) -> None:
        repo = InMemoryBettingRecordRepository()
        use_case = SettleBettingRecordUseCase(betting_record_repository=repo)

        with pytest.raises(BettingRecordNotFoundError):
            use_case.execute(
                user_id="user-001",
                record_id="nonexistent",
                payout=500,
            )

    def test_他ユーザーの記録は確定できない(self) -> None:
        repo = InMemoryBettingRecordRepository()
        record = _make_record(user_id="user-002")
        repo.save(record)
        use_case = SettleBettingRecordUseCase(betting_record_repository=repo)

        with pytest.raises(BettingRecordNotFoundError):
            use_case.execute(
                user_id="user-001",
                record_id=record.record_id.value,
                payout=500,
            )

    def test_確定済み記録は再確定できない(self) -> None:
        repo = InMemoryBettingRecordRepository()
        record = _make_record()
        record.settle(Money.of(500))
        repo.save(record)
        use_case = SettleBettingRecordUseCase(betting_record_repository=repo)

        with pytest.raises(ValueError):
            use_case.execute(
                user_id="user-001",
                record_id=record.record_id.value,
                payout=1000,
            )
