"""投票記録リポジトリインターフェース."""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from ..entities import BettingRecord
from ..enums import BetType
from ..identifiers import BettingRecordId, UserId


class BettingRecordRepository(ABC):
    """投票記録リポジトリのインターフェース."""

    @abstractmethod
    def save(self, record: BettingRecord) -> None:
        """投票記録を保存する."""
        pass

    @abstractmethod
    def find_by_id(self, record_id: BettingRecordId) -> BettingRecord | None:
        """投票記録IDで検索する."""
        pass

    @abstractmethod
    def find_by_user_id(
        self,
        user_id: UserId,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        venue: Optional[str] = None,
        bet_type: Optional[BetType] = None,
    ) -> list[BettingRecord]:
        """ユーザーIDで検索する（フィルタ付き）."""
        pass
