"""負け額限度額API ハンドラーのテスト."""
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from src.api.dependencies import Dependencies
from src.api.handlers.loss_limit import (
    check_loss_limit_handler,
    get_loss_limit_handler,
    set_loss_limit_handler,
    update_loss_limit_handler,
)
from src.domain.entities import LossLimitChange, User
from src.domain.enums import AuthProvider, LossLimitChangeStatus, LossLimitChangeType
from src.domain.identifiers import LossLimitChangeId, UserId
from src.domain.value_objects import DateOfBirth, DisplayName, Email, Money
from src.infrastructure.repositories import (
    InMemoryLossLimitChangeRepository,
    InMemoryUserRepository,
)


def _make_event(sub: str | None = None, body: dict | None = None, query: dict | None = None) -> dict:
    """テスト用イベントを作成する."""
    event: dict = {}
    if sub is not None:
        event["requestContext"] = {
            "authorizer": {"claims": {"sub": sub}}
        }
    if body is not None:
        event["body"] = json.dumps(body)
    if query is not None:
        event["queryStringParameters"] = query
    return event


def _make_user(**overrides) -> User:
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


@pytest.fixture(autouse=True)
def _reset_dependencies():
    Dependencies.reset()
    user_repo = InMemoryUserRepository()
    change_repo = InMemoryLossLimitChangeRepository()
    Dependencies.set_user_repository(user_repo)
    Dependencies.set_loss_limit_change_repository(change_repo)
    yield
    Dependencies.reset()


class TestGetLossLimit:
    """限度額取得のテスト."""

    def test_限度額を取得できる(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000), total_loss_this_month=Money.of(10000)))
        event = _make_event(sub="user-123")
        resp = get_loss_limit_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["loss_limit"] == 50000
        assert body["remaining_amount"] == 40000
        assert body["total_loss_this_month"] == 10000
        assert body["pending_changes"] == []

    def test_限度額未設定(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user())
        event = _make_event(sub="user-123")
        resp = get_loss_limit_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["loss_limit"] is None
        assert body["remaining_amount"] is None

    def test_保留中の変更リクエストを含む(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000)))
        change_repo = Dependencies.get_loss_limit_change_repository()
        change_repo.save(LossLimitChange(
            change_id=LossLimitChangeId("change-1"),
            user_id=UserId("user-123"),
            current_limit=Money.of(50000),
            requested_limit=Money.of(100000),
            change_type=LossLimitChangeType.INCREASE,
            status=LossLimitChangeStatus.PENDING,
            effective_at=datetime.now(timezone.utc) + timedelta(days=7),
        ))
        event = _make_event(sub="user-123")
        resp = get_loss_limit_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert len(body["pending_changes"]) == 1
        assert body["pending_changes"][0]["requested_limit"] == 100000

    def test_未認証で401(self):
        resp = get_loss_limit_handler(_make_event(), None)
        assert resp["statusCode"] == 401

    def test_存在しないユーザーで404(self):
        event = _make_event(sub="nonexistent")
        resp = get_loss_limit_handler(event, None)
        assert resp["statusCode"] == 404


class TestSetLossLimit:
    """限度額設定のテスト."""

    def test_限度額を設定できる(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user())
        event = _make_event(sub="user-123", body={"amount": 50000})
        resp = set_loss_limit_handler(event, None)
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["loss_limit"] == 50000

    def test_未認証で401(self):
        resp = set_loss_limit_handler(_make_event(body={"amount": 50000}), None)
        assert resp["statusCode"] == 401

    def test_amountなしで400(self):
        event = _make_event(sub="user-123", body={})
        resp = set_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400

    def test_amountが整数でないと400(self):
        event = _make_event(sub="user-123", body={"amount": "50000"})
        resp = set_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400

    def test_範囲外の金額で400(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user())
        event = _make_event(sub="user-123", body={"amount": 999})
        resp = set_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400

    def test_既に設定済みで400(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000)))
        event = _make_event(sub="user-123", body={"amount": 30000})
        resp = set_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400


class TestUpdateLossLimit:
    """限度額変更のテスト."""

    def test_減額できる(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000)))
        event = _make_event(sub="user-123", body={"amount": 30000})
        resp = update_loss_limit_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["applied_immediately"] is True
        assert body["requested_limit"] == 30000

    def test_増額はPENDINGになる(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000)))
        event = _make_event(sub="user-123", body={"amount": 100000})
        resp = update_loss_limit_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["applied_immediately"] is False
        assert body["change_type"] == "increase"

    def test_未認証で401(self):
        resp = update_loss_limit_handler(_make_event(body={"amount": 30000}), None)
        assert resp["statusCode"] == 401

    def test_amountなしで400(self):
        event = _make_event(sub="user-123", body={})
        resp = update_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400

    def test_限度額未設定で400(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user())
        event = _make_event(sub="user-123", body={"amount": 50000})
        resp = update_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400

    def test_同額変更で400(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000)))
        event = _make_event(sub="user-123", body={"amount": 50000})
        resp = update_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert "same" in body["error"]["message"].lower()

    def test_PENDING中に新規リクエストで400(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000)))
        # 増額リクエスト（PENDING状態になる）
        event = _make_event(sub="user-123", body={"amount": 100000})
        resp = update_loss_limit_handler(event, None)
        assert resp["statusCode"] == 200
        # さらに変更リクエストを出すと400
        event2 = _make_event(sub="user-123", body={"amount": 80000})
        resp2 = update_loss_limit_handler(event2, None)
        assert resp2["statusCode"] == 400
        body = json.loads(resp2["body"])
        assert "pending" in body["error"]["message"].lower()


class TestCheckLossLimit:
    """購入可否チェックのテスト."""

    def test_購入可能(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000), total_loss_this_month=Money.of(10000)))
        event = _make_event(sub="user-123", query={"amount": "5000"})
        resp = check_loss_limit_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["can_purchase"] is True

    def test_購入不可(self):
        repo = Dependencies.get_user_repository()
        repo.save(_make_user(loss_limit=Money.of(50000), total_loss_this_month=Money.of(45000)))
        event = _make_event(sub="user-123", query={"amount": "10000"})
        resp = check_loss_limit_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["can_purchase"] is False
        assert body["warning_level"] == "warning"

    def test_未認証で401(self):
        resp = check_loss_limit_handler(_make_event(query={"amount": "5000"}), None)
        assert resp["statusCode"] == 401

    def test_amountなしで400(self):
        event = _make_event(sub="user-123")
        resp = check_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400

    def test_amountが数値でないと400(self):
        event = _make_event(sub="user-123", query={"amount": "abc"})
        resp = check_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400

    def test_amountが0以下で400(self):
        event = _make_event(sub="user-123", query={"amount": "0"})
        resp = check_loss_limit_handler(event, None)
        assert resp["statusCode"] == 400
