"""LossLimitServiceのテスト."""
from datetime import date, datetime, timedelta, timezone

import pytest

from src.domain.entities import User
from src.domain.entities.loss_limit_change import LossLimitChange
from src.domain.enums import (
    AuthProvider,
    LossLimitChangeStatus,
    LossLimitChangeType,
    WarningLevel,
)
from src.domain.identifiers import UserId
from src.domain.services.loss_limit_service import LossLimitService
from src.domain.value_objects import DateOfBirth, DisplayName, Email, Money


def _make_user(**overrides) -> User:
    """テスト用ユーザーを作成する."""
    defaults = {
        "user_id": UserId("user-123"),
        "email": Email("test@example.com"),
        "display_name": DisplayName("太郎"),
        "date_of_birth": DateOfBirth(date(2000, 1, 1)),
        "terms_accepted_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "privacy_accepted_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "auth_provider": AuthProvider.COGNITO,
    }
    defaults.update(overrides)
    return User(**defaults)


class TestRequestChange:
    """LossLimitService.request_changeのテスト."""

    def test_増額リクエストを作成できる(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))

        change = service.request_change(user, Money.of(100000))

        assert change.change_type == LossLimitChangeType.INCREASE
        assert change.status == LossLimitChangeStatus.PENDING
        assert change.current_limit == Money.of(50000)
        assert change.requested_limit == Money.of(100000)

    def test_減額リクエストは即時承認される(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(100000))

        change = service.request_change(user, Money.of(50000))

        assert change.change_type == LossLimitChangeType.DECREASE
        assert change.status == LossLimitChangeStatus.APPROVED

    def test_減額時にユーザーのloss_limitが即時反映される(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(100000))

        service.request_change(user, Money.of(50000))

        assert user.loss_limit == Money.of(50000)

    def test_増額時にユーザーのloss_limitは変更されない(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))

        service.request_change(user, Money.of(100000))

        assert user.loss_limit == Money.of(50000)

    def test_loss_limit未設定ユーザーの初回設定(self):
        service = LossLimitService()
        user = _make_user()

        change = service.request_change(user, Money.of(50000))

        # 初回設定は減額扱い（即時反映）
        assert change.status == LossLimitChangeStatus.APPROVED
        assert user.loss_limit == Money.of(50000)


class TestCheckLimit:
    """LossLimitService.check_limitのテスト."""

    def test_limit未設定で購入可能(self):
        service = LossLimitService()
        user = _make_user()

        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        assert result.remaining_limit is None
        assert result.warning_level == WarningLevel.NONE

    def test_limit範囲内で購入可能(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))

        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        assert result.remaining_limit == Money.of(50000)
        assert result.warning_level == WarningLevel.NONE

    def test_limit超過で購入不可(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(45000))

        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is False
        assert result.remaining_limit == Money.of(5000)
        assert result.warning_level == WarningLevel.WARNING

    def test_limit80パーセント接近で注意(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(35000))

        # 残り15000に対して10000の賭けは (35000+10000)/50000 = 90% > 80%
        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        assert result.warning_level == WarningLevel.CAUTION

    def test_limitちょうどで購入可能(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(40000))

        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        assert result.remaining_limit == Money.of(10000)

    def test_残り限度額ゼロで購入不可(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(50000))

        result = service.check_limit(user, Money.of(100))

        assert result.can_purchase is False
        assert result.remaining_limit == Money.zero()
        assert result.warning_level == WarningLevel.WARNING


class TestProcessPendingChanges:
    """LossLimitService.process_pending_changesのテスト."""

    def test_有効期限到達の変更を適用できる(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))

        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        # effective_atを過去に設定
        change.effective_at = datetime.now(timezone.utc) - timedelta(hours=1)
        change.approve()

        service.process_pending_changes([change], user)

        assert user.loss_limit == Money.of(100000)

    def test_有効期限未到達の変更は適用されない(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))

        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        # PENDINGのまま（effective_atは7日後）

        service.process_pending_changes([change], user)

        assert user.loss_limit == Money.of(50000)

    def test_rejected状態の変更は適用されない(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))

        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        change.reject()

        service.process_pending_changes([change], user)

        assert user.loss_limit == Money.of(50000)
