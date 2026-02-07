"""SecretsManager による IPAT 認証情報プロバイダー実装."""
import json
import logging

import boto3
from botocore.exceptions import ClientError

from src.domain.identifiers import UserId
from src.domain.ports import IpatCredentialsProvider
from src.domain.value_objects import IpatCredentials

logger = logging.getLogger(__name__)


class SecretsManagerCredentialsProvider(IpatCredentialsProvider):
    """AWS Secrets Manager を使った IPAT 認証情報プロバイダー."""

    SECRET_PREFIX = "baken-kaigi/ipat/"

    def __init__(self) -> None:
        """初期化."""
        self._client = boto3.client("secretsmanager")

    def _secret_name(self, user_id: UserId) -> str:
        return f"{self.SECRET_PREFIX}{user_id.value}"

    def get_credentials(self, user_id: UserId) -> IpatCredentials | None:
        """ユーザーのIPAT認証情報を取得する."""
        try:
            response = self._client.get_secret_value(
                SecretId=self._secret_name(user_id),
            )
            data = json.loads(response["SecretString"])
            # 旧キー（card_number/birthday/dummy_pin）からのマイグレーション
            if "card_number" in data and "inet_id" not in data:
                logger.info(f"Migrating legacy credentials for {user_id}")
                migrated = IpatCredentials(
                    inet_id=data["card_number"][:8] if len(data["card_number"]) >= 8 else data["card_number"],
                    subscriber_number=data["birthday"],
                    pin=data["pin"],
                    pars_number=data["dummy_pin"],
                )
                self.save_credentials(user_id, migrated)
                return migrated
            return IpatCredentials(
                inet_id=data["inet_id"],
                subscriber_number=data["subscriber_number"],
                pin=data["pin"],
                pars_number=data["pars_number"],
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            logger.error(f"Failed to get credentials for {user_id}: {e}")
            raise

    def save_credentials(self, user_id: UserId, credentials: IpatCredentials) -> None:
        """ユーザーのIPAT認証情報を保存する."""
        secret_value = json.dumps({
            "inet_id": credentials.inet_id,
            "subscriber_number": credentials.subscriber_number,
            "pin": credentials.pin,
            "pars_number": credentials.pars_number,
        })
        try:
            self._client.put_secret_value(
                SecretId=self._secret_name(user_id),
                SecretString=secret_value,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                self._client.create_secret(
                    Name=self._secret_name(user_id),
                    SecretString=secret_value,
                )
            else:
                logger.error(f"Failed to save credentials for {user_id}: {e}")
                raise

    def delete_credentials(self, user_id: UserId) -> None:
        """ユーザーのIPAT認証情報を削除する."""
        try:
            self._client.delete_secret(
                SecretId=self._secret_name(user_id),
                ForceDeleteWithoutRecovery=True,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return
            logger.error(f"Failed to delete credentials for {user_id}: {e}")
            raise

    def has_credentials(self, user_id: UserId) -> bool:
        """ユーザーがIPAT認証情報を持っているか判定する."""
        try:
            self._client.describe_secret(
                SecretId=self._secret_name(user_id),
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            logger.error(f"Failed to check credentials for {user_id}: {e}")
            raise
