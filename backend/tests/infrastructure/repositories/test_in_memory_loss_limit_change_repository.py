"""InMemoryLossLimitChangeRepositoryのテスト."""
from datetime import datetime, timedelta, timezone

from src.domain.entities import LossLimitChange
from src.domain.enums import LossLimitChangeStatus, LossLimitChangeType
from src.domain.identifiers import LossLimitChangeId, UserId
from src.domain.value_objects import Money
from src.infrastructure.repositories import InMemoryLossLimitChangeRepository


def _make_change(**overrides) -> LossLimitChange:
    """テスト用変更リクエストを作成する."""
    defaults = {
        "change_id": LossLimitChangeId("change-123"),
        "user_id": UserId("user-123"),
        "current_limit": Money.of(50000),
        "requested_limit": Money.of(30000),
        "change_type": LossLimitChangeType.DECREASE,
        "status": LossLimitChangeStatus.APPROVED,
        "effective_at": datetime.now(timezone.utc),
        "requested_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return LossLimitChange(**defaults)


class TestInMemoryLossLimitChangeRepository:
    """InMemoryLossLimitChangeRepositoryのテスト."""

    def test_保存と取得(self):
        repo = InMemoryLossLimitChangeRepository()
        change = _make_change()
        repo.save(change)
        found = repo.find_by_id(LossLimitChangeId("change-123"))
        assert found is not None
        assert found.change_id.value == "change-123"

    def test_存在しないIDの検索(self):
        repo = InMemoryLossLimitChangeRepository()
        assert repo.find_by_id(LossLimitChangeId("nonexistent")) is None

    def test_ユーザーIDで検索(self):
        repo = InMemoryLossLimitChangeRepository()
        change1 = _make_change(change_id=LossLimitChangeId("change-1"))
        change2 = _make_change(
            change_id=LossLimitChangeId("change-2"),
            user_id=UserId("user-456"),
        )
        repo.save(change1)
        repo.save(change2)
        results = repo.find_by_user_id(UserId("user-123"))
        assert len(results) == 1
        assert results[0].change_id.value == "change-1"

    def test_保留中の変更をユーザーIDで検索(self):
        repo = InMemoryLossLimitChangeRepository()
        pending = _make_change(
            change_id=LossLimitChangeId("change-1"),
            status=LossLimitChangeStatus.PENDING,
            change_type=LossLimitChangeType.INCREASE,
            requested_limit=Money.of(100000),
            effective_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        approved = _make_change(
            change_id=LossLimitChangeId("change-2"),
            status=LossLimitChangeStatus.APPROVED,
        )
        repo.save(pending)
        repo.save(approved)
        results = repo.find_pending_by_user_id(UserId("user-123"))
        assert len(results) == 1
        assert results[0].change_id.value == "change-1"
        assert results[0].status == LossLimitChangeStatus.PENDING

    def test_空のリポジトリで検索(self):
        repo = InMemoryLossLimitChangeRepository()
        assert repo.find_by_user_id(UserId("user-123")) == []
        assert repo.find_pending_by_user_id(UserId("user-123")) == []

    def test_上書き保存(self):
        repo = InMemoryLossLimitChangeRepository()
        change = _make_change(status=LossLimitChangeStatus.PENDING)
        repo.save(change)
        change.approve()
        repo.save(change)
        found = repo.find_by_id(LossLimitChangeId("change-123"))
        assert found is not None
        assert found.status == LossLimitChangeStatus.APPROVED
