"""負け額限度額サービス."""
from __future__ import annotations

from datetime import datetime, timezone

from ..entities.loss_limit_change import LossLimitChange
from ..entities.user import User
from ..enums import LossLimitChangeStatus, LossLimitChangeType, WarningLevel
from ..identifiers import LossLimitChangeId
from ..value_objects import Money
from ..value_objects.loss_limit_check_result import LossLimitCheckResult


class LossLimitService:
    """負け額限度額に関するドメインサービス."""

    def request_change(self, user: User, new_limit: Money) -> LossLimitChange:
        """限度額の変更をリクエストする."""
        is_initial_setup = user.loss_limit is None
        current_limit = user.loss_limit if user.loss_limit is not None else Money.zero()

        if is_initial_setup:
            # 初回設定は即時反映
            change = LossLimitChange(
                change_id=LossLimitChangeId.generate(),
                user_id=user.user_id,
                current_limit=current_limit,
                requested_limit=new_limit,
                change_type=LossLimitChangeType.DECREASE,
                status=LossLimitChangeStatus.APPROVED,
                effective_at=datetime.now(timezone.utc),
            )
            user.set_loss_limit(new_limit)
            return change

        change = LossLimitChange.create(
            user_id=user.user_id,
            current_limit=current_limit,
            requested_limit=new_limit,
        )

        # 減額（即時反映）の場合、ユーザーに即座に反映
        if change.is_effective():
            user.set_loss_limit(new_limit)

        return change

    def check_limit(self, user: User, bet_amount: Money) -> LossLimitCheckResult:
        """購入可否を判定する."""
        if user.loss_limit is None:
            return LossLimitCheckResult(
                can_purchase=True,
                remaining_amount=None,
                warning_level=WarningLevel.NONE,
                message="限度額が設定されていません",
            )

        remaining = user.get_remaining_loss_limit()

        if remaining == Money.zero():
            return LossLimitCheckResult(
                can_purchase=False,
                remaining_amount=Money.zero(),
                warning_level=WarningLevel.WARNING,
                message="限度額に達しています",
            )

        # 賭けた場合の累計損失を計算
        potential_total = user.total_loss_this_month.add(bet_amount)
        can_purchase = potential_total.is_less_than_or_equal(user.loss_limit)

        if not can_purchase:
            return LossLimitCheckResult(
                can_purchase=False,
                remaining_amount=remaining,
                warning_level=WarningLevel.WARNING,
                message="限度額を超過しています",
            )

        # 賭け後の残額を計算
        remaining_after_bet = remaining.subtract(bet_amount)

        # 使用率で警告レベルを判定
        usage_ratio = potential_total.value / user.loss_limit.value
        if usage_ratio >= 0.8:
            return LossLimitCheckResult(
                can_purchase=True,
                remaining_amount=remaining_after_bet,
                warning_level=WarningLevel.CAUTION,
                message=f"限度額の80%以上に達しています（残り: {remaining_after_bet.value}円）",
            )

        return LossLimitCheckResult(
            can_purchase=True,
            remaining_amount=remaining_after_bet,
            warning_level=WarningLevel.NONE,
            message=f"購入可能です（残り: {remaining_after_bet.value}円）",
        )

    def process_pending_changes(
        self,
        changes: list[LossLimitChange],
        user: User,
        now: datetime | None = None,
    ) -> None:
        """待機期間完了した変更を適用する."""
        effective_now = now or datetime.now(timezone.utc)
        for change in changes:
            # PENDING で待機期間経過 → 自動承認
            if (
                change.status == LossLimitChangeStatus.PENDING
                and change.effective_at is not None
                and change.effective_at <= effective_now
            ):
                change.approve()

            if change.is_effective(effective_now):
                user.set_loss_limit(change.requested_limit)
