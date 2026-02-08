"""CreateBettingRecordUseCase のテスト."""
from datetime import date

from src.application.use_cases.create_betting_record import CreateBettingRecordUseCase
from src.domain.enums import BetType, BettingRecordStatus
from src.infrastructure.repositories.in_memory_betting_record_repository import (
    InMemoryBettingRecordRepository,
)


class TestCreateBettingRecordUseCase:
    """CreateBettingRecordUseCase のテスト."""

    def test_投票記録を作成できる(self) -> None:
        repo = InMemoryBettingRecordRepository()
        use_case = CreateBettingRecordUseCase(betting_record_repository=repo)

        record = use_case.execute(
            user_id="user-001",
            race_id="202605051211",
            race_name="東京11R 日本ダービー",
            race_date="2026-05-05",
            venue="東京",
            bet_type="win",
            horse_numbers=[1],
            amount=100,
        )

        assert record.user_id.value == "user-001"
        assert record.race_id.value == "202605051211"
        assert record.race_name == "東京11R 日本ダービー"
        assert record.race_date == date(2026, 5, 5)
        assert record.venue == "東京"
        assert record.bet_type == BetType.WIN
        assert record.horse_numbers.numbers == (1,)
        assert record.amount.value == 100
        assert record.status == BettingRecordStatus.PENDING
        assert record.payout.value == 0

    def test_作成した記録がリポジトリに保存される(self) -> None:
        repo = InMemoryBettingRecordRepository()
        use_case = CreateBettingRecordUseCase(betting_record_repository=repo)

        record = use_case.execute(
            user_id="user-001",
            race_id="202605051211",
            race_name="東京11R",
            race_date="2026-05-05",
            venue="東京",
            bet_type="win",
            horse_numbers=[1],
            amount=100,
        )

        saved = repo.find_by_id(record.record_id)
        assert saved is not None
        assert saved.record_id == record.record_id

    def test_三連単の投票記録を作成できる(self) -> None:
        repo = InMemoryBettingRecordRepository()
        use_case = CreateBettingRecordUseCase(betting_record_repository=repo)

        record = use_case.execute(
            user_id="user-001",
            race_id="202605051211",
            race_name="東京11R",
            race_date="2026-05-05",
            venue="東京",
            bet_type="trifecta",
            horse_numbers=[3, 5, 8],
            amount=500,
        )

        assert record.bet_type == BetType.TRIFECTA
        assert record.horse_numbers.numbers == (3, 5, 8)
        assert record.amount.value == 500
