"""投票成績サマリー取得ユースケース."""
from datetime import date, datetime

from src.domain.identifiers import UserId
from src.domain.ports import BettingRecordRepository
from src.domain.value_objects import BettingSummary


class GetBettingSummaryUseCase:
    """投票成績サマリー取得ユースケース."""

    def __init__(self, betting_record_repository: BettingRecordRepository) -> None:
        """初期化."""
        self._betting_record_repository = betting_record_repository

    def execute(self, user_id: str, period: str = "all_time") -> BettingSummary:
        """投票成績のサマリーを取得する."""
        from_date, to_date = self._get_date_range(period)

        records = self._betting_record_repository.find_by_user_id(
            user_id=UserId(user_id),
            from_date=from_date,
            to_date=to_date,
        )

        return BettingSummary.from_records(records)

    @staticmethod
    def _get_date_range(period: str) -> tuple[date | None, date | None]:
        """期間に応じた日付範囲を返す."""
        now = datetime.now()

        if period == "this_month":
            from_date = date(now.year, now.month, 1)
            return from_date, None

        if period == "last_month":
            if now.month == 1:
                from_date = date(now.year - 1, 12, 1)
                to_date = date(now.year - 1, 12, 31)
            else:
                from_date = date(now.year, now.month - 1, 1)
                import calendar
                last_day = calendar.monthrange(now.year, now.month - 1)[1]
                to_date = date(now.year, now.month - 1, last_day)
            return from_date, to_date

        # all_time
        return None, None
