"""DynamoDB ユーザーリポジトリ実装."""
import os
from datetime import date, datetime

import boto3
from boto3.dynamodb.conditions import Key

from src.domain.entities import User
from src.domain.enums import AuthProvider, UserStatus
from src.domain.identifiers import UserId
from src.domain.ports.user_repository import UserRepository
from src.domain.value_objects import DateOfBirth, DisplayName, Email


class DynamoDBUserRepository(UserRepository):
    """DynamoDB ユーザーリポジトリ."""

    def __init__(self) -> None:
        """初期化."""
        self._table_name = os.environ.get("USER_TABLE_NAME", "baken-kaigi-user")
        self._dynamodb = boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(self._table_name)

    def save(self, user: User) -> None:
        """ユーザーを保存する."""
        item = self._to_dynamodb_item(user)
        self._table.put_item(Item=item)

    def find_by_id(self, user_id: UserId) -> User | None:
        """ユーザーIDで検索する."""
        response = self._table.get_item(Key={"user_id": user_id.value})
        item = response.get("Item")
        if item is None:
            return None
        return self._from_dynamodb_item(item)

    def find_by_email(self, email: Email) -> User | None:
        """メールアドレスで検索する."""
        response = self._table.query(
            IndexName="email-index",
            KeyConditionExpression=Key("email").eq(email.value),
        )
        items = response.get("Items", [])
        if not items:
            return None
        return self._from_dynamodb_item(items[0])

    def delete(self, user_id: UserId) -> None:
        """ユーザーを削除する."""
        self._table.delete_item(Key={"user_id": user_id.value})

    @staticmethod
    def _to_dynamodb_item(user: User) -> dict:
        """User を DynamoDB アイテムに変換する."""
        item: dict = {
            "user_id": user.user_id.value,
            "email": user.email.value,
            "display_name": user.display_name.value,
            "date_of_birth": user.date_of_birth.value.isoformat(),
            "terms_accepted_at": user.terms_accepted_at.isoformat(),
            "privacy_accepted_at": user.privacy_accepted_at.isoformat(),
            "auth_provider": user.auth_provider.value,
            "status": user.status.value,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
        if user.deletion_requested_at is not None:
            item["deletion_requested_at"] = user.deletion_requested_at.isoformat()
        return item

    @staticmethod
    def _from_dynamodb_item(item: dict) -> User:
        """DynamoDB アイテムから User を復元する."""
        date_parts = item["date_of_birth"].split("-")
        dob = date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))

        deletion_requested_at = None
        if item.get("deletion_requested_at"):
            deletion_requested_at = datetime.fromisoformat(item["deletion_requested_at"])

        return User(
            user_id=UserId(item["user_id"]),
            email=Email(item["email"]),
            display_name=DisplayName(item["display_name"]),
            date_of_birth=DateOfBirth(dob),
            terms_accepted_at=datetime.fromisoformat(item["terms_accepted_at"]),
            privacy_accepted_at=datetime.fromisoformat(item["privacy_accepted_at"]),
            auth_provider=AuthProvider(item["auth_provider"]),
            status=UserStatus(item["status"]),
            deletion_requested_at=deletion_requested_at,
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )
