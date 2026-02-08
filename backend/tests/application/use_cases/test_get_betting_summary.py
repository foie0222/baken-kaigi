"""GetBettingSummaryUseCase のテスト."""
from datetime import date, datetime

from src.application.use_cases.get_betting_summary import GetBettingSummaryUseCase
from src.domain.entities import BettingRecord
from src.domain.enums import BetType
from src.domain.identifiers import RaceId, UserId
from src.domain.value_objects import HorseNumbers, Money
from src.infrastructure.repositories.in_memory_betting_record_repository import (
    InMemoryBettingRecordRepository,
)


def _make_settled_record(
    user_id: str = "user-001",
    race_date: date = date(2026, 2, 1),
    amount: int = 100,
    payout: int = 0,
) -> BettingRecord:
    record = BettingRecord.create(
        user_id=UserId(user_id),
        race_id=RaceId("202602011211"),
        race_name="東京11R",
        race_date=race_date,
        venue="東京",
        bet_type=BetType.WIN,
        horse_numbers=HorseNumbers.of(1),
        amount=Money.of(amount),
    )
    record.settle(Money.of(payout))
    return record


class TestGetBettingSummaryUseCase:
    """GetBettingSummaryUseCase のテスト."""

    def test_全期間のサマリーを取得できる(self) -> None:
        repo = InMemoryBettingRecordRepository()
        repo.save(_make_settled_record(amount=100, payout=300))
        repo.save(_make_settled_record(amount=200, payout=0))
        use_case = GetBettingSummaryUseCase(betting_record_repository=repo)

        summary = use_case.execute(user_id="user-001", period="all_time")

        assert summary.total_investment.value == 300
        assert summary.total_payout.value == 300
        assert summary.record_count == 2
        assert summary.win_rate == 0.5

    def test_今月のサマリーを取得できる(self) -> None:
        repo = InMemoryBettingRecordRepository()
        now = datetime.now()
        this_month = date(now.year, now.month, 1)
        repo.save(_make_settled_record(race_date=this_month, amount=100, payout=500))
        repo.save(_make_settled_record(race_date=date(2020, 1, 1), amount=100, payout=0))
        use_case = GetBettingSummaryUseCase(betting_record_repository=repo)

        summary = use_case.execute(user_id="user-001", period="this_month")

        assert summary.record_count == 1
        assert summary.total_investment.value == 100
        assert summary.total_payout.value == 500

    def test_先月のサマリーを取得できる(self) -> None:
        repo = InMemoryBettingRecordRepository()
        now = datetime.now()
        if now.month == 1:
            last_month = date(now.year - 1, 12, 15)
        else:
            last_month = date(now.year, now.month - 1, 15)
        repo.save(_make_settled_record(race_date=last_month, amount=200, payout=1000))
        repo.save(_make_settled_record(race_date=date(2020, 1, 1), amount=100, payout=0))
        use_case = GetBettingSummaryUseCase(betting_record_repository=repo)

        summary = use_case.execute(user_id="user-001", period="last_month")

        assert summary.record_count == 1
        assert summary.total_investment.value == 200

    def test_記録なしで空サマリー(self) -> None:
        repo = InMemoryBettingRecordRepository()
        use_case = GetBettingSummaryUseCase(betting_record_repository=repo)

        summary = use_case.execute(user_id="user-001", period="all_time")

        assert summary.record_count == 0
        assert summary.total_investment.value == 0
        assert summary.total_payout.value == 0
        assert summary.win_rate == 0.0
