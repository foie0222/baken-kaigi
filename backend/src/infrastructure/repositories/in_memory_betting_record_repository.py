"""投票記録リポジトリのインメモリ実装."""
from datetime import date
from typing import Optional

from src.domain.entities import BettingRecord
from src.domain.enums import BetType
from src.domain.identifiers import BettingRecordId, UserId
from src.domain.ports import BettingRecordRepository


class InMemoryBettingRecordRepository(BettingRecordRepository):
    """投票記録リポジトリのインメモリ実装."""

    def __init__(self) -> None:
        """初期化."""
        self._records: dict[str, BettingRecord] = {}

    def save(self, record: BettingRecord) -> None:
        """投票記録を保存する."""
        self._records[record.record_id.value] = record

    def find_by_id(self, record_id: BettingRecordId) -> BettingRecord | None:
        """投票記録IDで検索する."""
        return self._records.get(record_id.value)

    def find_by_user_id(
        self,
        user_id: UserId,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        venue: Optional[str] = None,
        bet_type: Optional[BetType] = None,
    ) -> list[BettingRecord]:
        """ユーザーIDで検索する（フィルタ付き、新しい順）."""
        results = [
            r for r in self._records.values()
            if r.user_id == user_id
        ]

        if from_date is not None:
            results = [r for r in results if r.race_date >= from_date]
        if to_date is not None:
            results = [r for r in results if r.race_date <= to_date]
        if venue is not None:
            results = [r for r in results if r.venue == venue]
        if bet_type is not None:
            results = [r for r in results if r.bet_type == bet_type]

        return sorted(results, key=lambda r: r.created_at, reverse=True)
