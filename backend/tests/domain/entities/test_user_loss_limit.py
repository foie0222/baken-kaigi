"""UserエンティティのLoss Limit関連テスト."""
from datetime import date, datetime, timezone

import pytest

from src.domain.entities import User
from src.domain.enums import AuthProvider
from src.domain.identifiers import UserId
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


class TestUserLossLimit:
    """UserのLoss Limit関連テスト."""

    def test_デフォルトではloss_limitはNone(self):
        user = _make_user()
        assert user.loss_limit is None

    def test_デフォルトではtotal_loss_this_monthはゼロ(self):
        user = _make_user()
        assert user.total_loss_this_month == Money.zero()

    def test_デフォルトではloss_limit_set_atはNone(self):
        user = _make_user()
        assert user.loss_limit_set_at is None

    def test_loss_limitを設定できる(self):
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        assert user.loss_limit == Money.of(50000)
        assert user.loss_limit_set_at is not None

    def test_loss_limit設定時にupdated_atが更新される(self):
        user = _make_user()
        old_updated_at = user.updated_at
        user.set_loss_limit(Money.of(50000))
        assert user.updated_at > old_updated_at

    def test_loss_limitをゼロに設定するとエラー(self):
        user = _make_user()
        with pytest.raises(ValueError, match="must be positive"):
            user.set_loss_limit(Money.zero())

    def test_get_remaining_loss_limitでlimit未設定の場合None(self):
        user = _make_user()
        assert user.get_remaining_loss_limit() is None

    def test_get_remaining_loss_limitで残り限度額を取得(self):
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        assert user.get_remaining_loss_limit() == Money.of(50000)

    def test_get_remaining_loss_limitで損失記録後の残り限度額(self):
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(10000))
        assert user.get_remaining_loss_limit() == Money.of(40000)

    def test_get_remaining_loss_limitで損失が限度額を超えた場合ゼロ(self):
        user = _make_user()
        user.set_loss_limit(Money.of(50000))
        user.record_loss(Money.of(60000))
        assert user.get_remaining_loss_limit() == Money.zero()

    def test_record_lossで損失を記録(self):
        user = _make_user()
        user.record_loss(Money.of(10000))
        assert user.total_loss_this_month == Money.of(10000)

    def test_record_lossで累積される(self):
        user = _make_user()
        user.record_loss(Money.of(10000))
        user.record_loss(Money.of(5000))
        assert user.total_loss_this_month == Money.of(15000)

    def test_record_lossでゼロを記録してもエラーにならない(self):
        user = _make_user()
        user.record_loss(Money.zero())
        assert user.total_loss_this_month == Money.zero()

    def test_reset_monthly_lossで月初リセット(self):
        user = _make_user()
        user.record_loss(Money.of(30000))
        user.reset_monthly_loss()
        assert user.total_loss_this_month == Money.zero()

    def test_reset_monthly_lossでupdated_atが更新される(self):
        user = _make_user()
        user.record_loss(Money.of(30000))
        old_updated_at = user.updated_at
        user.reset_monthly_loss()
        assert user.updated_at > old_updated_at
