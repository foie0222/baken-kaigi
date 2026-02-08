"""DynamoDBUserRepositoryの負け額限度額フィールドのテスト."""
from datetime import date, datetime, timezone

from src.domain.entities import User
from src.domain.enums import AuthProvider
from src.domain.identifiers import UserId
from src.domain.value_objects import DateOfBirth, DisplayName, Email, Money
from src.infrastructure.repositories.dynamodb_user_repository import DynamoDBUserRepository


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


class TestDynamoDBUserRepositoryLossLimitSerialization:
    """DynamoDBUserRepositoryの負け額限度額シリアライズ/デシリアライズのテスト."""

    def test_loss_limitありでシリアライズ(self):
        user = _make_user(
            loss_limit=Money.of(50000),
            total_loss_this_month=Money.of(10000),
            loss_limit_set_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        item = DynamoDBUserRepository._to_dynamodb_item(user)
        assert item["loss_limit"] == 50000
        assert item["total_loss_this_month"] == 10000
        assert item["loss_limit_set_at"] == "2024-06-01T00:00:00+00:00"

    def test_loss_limitなしでシリアライズ(self):
        user = _make_user()
        item = DynamoDBUserRepository._to_dynamodb_item(user)
        assert "loss_limit" not in item
        assert item["total_loss_this_month"] == 0
        assert "loss_limit_set_at" not in item

    def test_loss_limitありでデシリアライズ(self):
        user = _make_user(
            loss_limit=Money.of(50000),
            total_loss_this_month=Money.of(10000),
            loss_limit_set_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        item = DynamoDBUserRepository._to_dynamodb_item(user)
        restored = DynamoDBUserRepository._from_dynamodb_item(item)
        assert restored.loss_limit == Money.of(50000)
        assert restored.total_loss_this_month == Money.of(10000)
        assert restored.loss_limit_set_at == datetime(2024, 6, 1, tzinfo=timezone.utc)

    def test_loss_limitなしでデシリアライズ(self):
        user = _make_user()
        item = DynamoDBUserRepository._to_dynamodb_item(user)
        restored = DynamoDBUserRepository._from_dynamodb_item(item)
        assert restored.loss_limit is None
        assert restored.total_loss_this_month == Money.zero()
        assert restored.loss_limit_set_at is None

    def test_既存データとの後方互換性_loss_limitフィールドなし(self):
        """既存のDynamoDBデータにloss_limit等のフィールドがない場合."""
        item = {
            "user_id": "user-123",
            "email": "test@example.com",
            "display_name": "太郎",
            "date_of_birth": "2000-01-01",
            "terms_accepted_at": "2024-01-01T00:00:00+00:00",
            "privacy_accepted_at": "2024-01-01T00:00:00+00:00",
            "auth_provider": "cognito",
            "status": "active",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
        }
        restored = DynamoDBUserRepository._from_dynamodb_item(item)
        assert restored.loss_limit is None
        assert restored.total_loss_this_month == Money.zero()
        assert restored.loss_limit_set_at is None

    def test_ラウンドトリップ_loss_limitあり(self):
        """シリアライズ→デシリアライズで値が保存されること."""
        user = _make_user(
            loss_limit=Money.of(100000),
            total_loss_this_month=Money.of(25000),
            loss_limit_set_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        item = DynamoDBUserRepository._to_dynamodb_item(user)
        restored = DynamoDBUserRepository._from_dynamodb_item(item)
        assert restored.loss_limit == user.loss_limit
        assert restored.total_loss_this_month == user.total_loss_this_month
        assert restored.loss_limit_set_at == user.loss_limit_set_at
