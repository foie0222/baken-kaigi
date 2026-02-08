"""掛け金フィードバックを表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ..enums import WarningLevel

from .money import Money


@dataclass(frozen=True)
class AmountFeedback:
    """掛け金額に対するフィードバック."""

    total_amount: Money
    remaining_loss_limit: Money | None  # 残り許容負け額（ログイン時のみ）
    average_amount: Money | None  # 過去の平均掛け金（ログイン時のみ）
    is_limit_exceeded: bool
    warning_level: WarningLevel
    comment: str
    generated_at: datetime

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.comment:
            raise ValueError("Comment cannot be empty")

    @classmethod
    def create(
        cls,
        total_amount: Money,
        remaining_loss_limit: Money | None = None,
        average_amount: Money | None = None,
        generated_at: datetime | None = None,
    ) -> AmountFeedback:
        """フィードバックを生成する（警告レベルを自動判定）."""
        warning_level, is_exceeded = cls._determine_warning_level(
            total_amount, remaining_loss_limit
        )
        comment = cls._generate_comment(
            total_amount, remaining_loss_limit, warning_level
        )

        return cls(
            total_amount=total_amount,
            remaining_loss_limit=remaining_loss_limit,
            average_amount=average_amount,
            is_limit_exceeded=is_exceeded,
            warning_level=warning_level,
            comment=comment,
            generated_at=generated_at or datetime.now(timezone.utc),
        )

    @staticmethod
    def _determine_warning_level(
        total_amount: Money, remaining_loss_limit: Money | None
    ) -> tuple[WarningLevel, bool]:
        """警告レベルを判定する."""
        if remaining_loss_limit is None:
            return WarningLevel.NONE, False

        if remaining_loss_limit.value == 0:
            return WarningLevel.WARNING, total_amount.value > 0

        ratio = total_amount.value / remaining_loss_limit.value

        if ratio >= 1.0:
            return WarningLevel.WARNING, True
        elif ratio >= 0.8:
            return WarningLevel.CAUTION, False
        else:
            return WarningLevel.NONE, False

    @staticmethod
    def _generate_comment(
        total_amount: Money,
        remaining_loss_limit: Money | None,
        warning_level: WarningLevel,
    ) -> str:
        """フィードバックコメントを生成する."""
        if remaining_loss_limit is None:
            return f"合計掛け金は{total_amount.format()}です。"

        if warning_level == WarningLevel.WARNING:
            return (
                f"合計掛け金{total_amount.format()}は、"
                f"残り許容負け額{remaining_loss_limit.format()}を超えています。"
            )
        elif warning_level == WarningLevel.CAUTION:
            return (
                f"合計掛け金{total_amount.format()}は、"
                f"残り許容負け額{remaining_loss_limit.format()}の80%を超えています。"
            )
        else:
            return (
                f"合計掛け金{total_amount.format()}は、"
                f"残り許容負け額{remaining_loss_limit.format()}の範囲内です。"
            )
