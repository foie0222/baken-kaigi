"""LossLimitChangeエンティティのテスト."""
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.entities.loss_limit_change import LossLimitChange
from src.domain.enums import LossLimitChangeStatus, LossLimitChangeType
from src.domain.identifiers import LossLimitChangeId, UserId
from src.domain.value_objects import Money


class TestLossLimitChangeCreate:
    """LossLimitChange.createファクトリメソッドのテスト."""

    def test_増額リクエストを作成できる(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        assert change.user_id == UserId("user-123")
        assert change.current_limit == Money.of(50000)
        assert change.requested_limit == Money.of(100000)
        assert change.change_type == LossLimitChangeType.INCREASE
        assert change.status == LossLimitChangeStatus.PENDING
        assert change.change_id is not None

    def test_増額リクエストのeffective_atは7日後(self):
        now = datetime.now(timezone.utc)
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        expected_min = now + timedelta(days=7) - timedelta(seconds=5)
        expected_max = now + timedelta(days=7) + timedelta(seconds=5)
        assert expected_min <= change.effective_at <= expected_max

    def test_減額リクエストを作成できる(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(100000),
            requested_limit=Money.of(50000),
        )
        assert change.change_type == LossLimitChangeType.DECREASE
        assert change.status == LossLimitChangeStatus.APPROVED

    def test_減額リクエストのeffective_atは即時(self):
        now = datetime.now(timezone.utc)
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(100000),
            requested_limit=Money.of(50000),
        )
        assert change.effective_at <= now + timedelta(seconds=5)

    def test_同額の変更リクエストでエラー(self):
        with pytest.raises(ValueError, match="same as current"):
            LossLimitChange.create(
                user_id=UserId("user-123"),
                current_limit=Money.of(50000),
                requested_limit=Money.of(50000),
            )

    def test_requested_atが設定される(self):
        now = datetime.now(timezone.utc)
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        assert change.requested_at >= now - timedelta(seconds=5)


class TestLossLimitChangeApprove:
    """LossLimitChange承認のテスト."""

    def test_pending状態の変更を承認できる(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        change.approve()
        assert change.status == LossLimitChangeStatus.APPROVED

    def test_approved状態の変更を承認するとエラー(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(100000),
            requested_limit=Money.of(50000),
        )
        # 減額は即座にAPPROVED
        with pytest.raises(ValueError, match="not pending"):
            change.approve()


class TestLossLimitChangeReject:
    """LossLimitChange却下のテスト."""

    def test_pending状態の変更を却下できる(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        change.reject()
        assert change.status == LossLimitChangeStatus.REJECTED

    def test_approved状態の変更を却下するとエラー(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(100000),
            requested_limit=Money.of(50000),
        )
        with pytest.raises(ValueError, match="not pending"):
            change.reject()


class TestLossLimitChangeIsEffective:
    """LossLimitChange有効判定のテスト."""

    def test_approved且つeffective_at到達済みで有効(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(100000),
            requested_limit=Money.of(50000),
        )
        # 減額は即座にAPPROVED・即時effective
        assert change.is_effective() is True

    def test_pending状態では無効(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        # 増額はPENDING
        assert change.is_effective() is False

    def test_rejected状態では無効(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        change.reject()
        assert change.is_effective() is False

    def test_now引数で有効期限判定できる(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        change.approve()
        # effective_at は 7日後なので、8日後の now を渡すと有効
        future = datetime.now(timezone.utc) + timedelta(days=8)
        assert change.is_effective(now=future) is True

    def test_now引数でeffective_at未到達なら無効(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
        )
        change.approve()
        # effective_at は 7日後なので、6日後の now を渡すと無効
        before = datetime.now(timezone.utc) + timedelta(days=6)
        assert change.is_effective(now=before) is False

    def test_now引数なしは後方互換(self):
        change = LossLimitChange.create(
            user_id=UserId("user-123"),
            current_limit=Money.of(100000),
            requested_limit=Money.of(50000),
        )
        # 減額は即時effective - now引数なしでも動作する
        assert change.is_effective() is True
