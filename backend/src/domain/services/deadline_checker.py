"""締め切りチェックサービス."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..identifiers import ItemId
from ..value_objects import RaceReference


@dataclass(frozen=True)
class DeadlineCheckResult:
    """締め切りチェック結果."""

    all_valid: bool  # 全て締め切り前か
    expired_items: list[ItemId]  # 締め切り切れアイテム
    nearest_deadline: datetime | None  # 最も近い締め切り


class DeadlineChecker:
    """投票締め切りのチェックサービス."""

    def is_before_deadline(self, race_ref: RaceReference, now: datetime) -> bool:
        """締め切り前かどうかを判定する."""
        return race_ref.is_before_deadline(now)

    def get_remaining_time(
        self, race_ref: RaceReference, now: datetime
    ) -> timedelta | None:
        """締め切りまでの残り時間を取得する."""
        return race_ref.get_remaining_time(now)

    def check_deadlines(
        self,
        race_references: dict[ItemId, RaceReference],
        now: datetime,
    ) -> DeadlineCheckResult:
        """複数のレース参照の締め切りをチェックする."""
        expired_items: list[ItemId] = []
        nearest_deadline: datetime | None = None

        for item_id, race_ref in race_references.items():
            if not race_ref.is_before_deadline(now):
                expired_items.append(item_id)
            else:
                if nearest_deadline is None or race_ref.betting_deadline < nearest_deadline:
                    nearest_deadline = race_ref.betting_deadline

        return DeadlineCheckResult(
            all_valid=len(expired_items) == 0,
            expired_items=expired_items,
            nearest_deadline=nearest_deadline,
        )
