"""LossLimitServiceのテスト."""
from datetime import date, datetime, timedelta, timezone

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
        assert result.remaining_amount is None
        assert result.warning_level == WarningLevel.NONE
        assert result.message == "限度額が設定されていません"

    def test_limit範囲内で購入可能(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))

        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        # 賭け後の残額: 50000 - 10000 = 40000
        assert result.remaining_amount == Money.of(40000)
        assert result.warning_level == WarningLevel.NONE

    def test_limit超過で購入不可(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(45000))

        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is False
        # 超過時の残額は賭け前の残り（5000円）を返す（賭けられないので差し引かない）
        assert result.remaining_amount == Money.of(5000)
        assert result.warning_level == WarningLevel.WARNING
        assert result.message == "限度額を超過しています"

    def test_limit80パーセント接近で注意(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(35000))

        # 残り15000に対して10000の賭けは (35000+10000)/50000 = 90% > 80%
        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        assert result.warning_level == WarningLevel.CAUTION
        # 賭け後の残額: 15000 - 10000 = 5000
        assert result.remaining_amount == Money.of(5000)
        assert "5000" in result.message

    def test_limitちょうどで購入可能(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(40000))

        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        # 賭け後の残額: 10000 - 10000 = 0
        assert result.remaining_amount == Money.of(0)
        # (40000+10000)/50000 = 1.0 → CAUTION
        assert result.warning_level == WarningLevel.CAUTION
        assert "0" in result.message

    def test_80パーセント境界値_ちょうど80パーセントでCAUTION(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(100000))
        user.record_loss(Money.of(70000))

        # (70000 + 10000) / 100000 = 0.8 → CAUTION
        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        assert result.warning_level == WarningLevel.CAUTION
        assert "80%以上" in result.message

    def test_80パーセント境界値_80パーセント未満ギリギリでNONE(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(100000))
        user.record_loss(Money.of(69000))

        # (69000 + 10000) / 100000 = 0.79 → NONE
        result = service.check_limit(user, Money.of(10000))

        assert result.can_purchase is True
        assert result.warning_level == WarningLevel.NONE
        # 賭け後の残額: 31000 - 10000 = 21000
        assert result.remaining_amount == Money.of(21000)
        assert "21000" in result.message

    def test_残り限度額ゼロで購入不可(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(50000))

        result = service.check_limit(user, Money.of(100))

        assert result.can_purchase is False
        assert result.remaining_amount == Money.zero()
        assert result.warning_level == WarningLevel.WARNING
        assert result.message == "限度額に達しています"


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
        # PENDINGのまま — process_pending_changesが自動承認する

        # effective_atは7日後なので、8日後のnowを渡す
        future = datetime.now(timezone.utc) + timedelta(days=8)
        service.process_pending_changes([change], user, now=future)

        assert user.loss_limit == Money.of(100000)
        assert change.status == LossLimitChangeStatus.APPROVED

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

    def test_空リストの場合は何もしない(self):
        service = LossLimitService()
        user = _make_user()
        user.set_loss_limit(Money.of(50000))

        service.process_pending_changes([], user)

        assert user.loss_limit == Money.of(50000)
