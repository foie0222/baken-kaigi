"""データに基づくフィードバックを表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..identifiers import ItemId

from .horse_data_summary import HorseDataSummary


@dataclass(frozen=True)
class DataFeedback:
    """選択した馬に関するデータに基づくフィードバック."""

    cart_item_id: ItemId
    horse_summaries: tuple[HorseDataSummary, ...]
    overall_comment: str
    generated_at: datetime

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.horse_summaries:
            raise ValueError("Horse summaries cannot be empty")
        if not self.overall_comment:
            raise ValueError("Overall comment cannot be empty")

    @classmethod
    def create(
        cls,
        cart_item_id: ItemId,
        horse_summaries: list[HorseDataSummary],
        overall_comment: str,
        generated_at: datetime | None = None,
    ) -> DataFeedback:
        """フィードバックを生成する."""
        return cls(
            cart_item_id=cart_item_id,
            horse_summaries=tuple(horse_summaries),
            overall_comment=overall_comment,
            generated_at=generated_at or datetime.now(),
        )

    def get_horse_summary(self, horse_number: int) -> HorseDataSummary | None:
        """指定馬番の要約を取得."""
        for summary in self.horse_summaries:
            if summary.horse_number == horse_number:
                return summary
        return None
