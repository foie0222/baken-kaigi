"""HRDBバッチLambda共通ヘルパー."""
import json
import logging
import os

import boto3

from src.infrastructure.clients.hrdb_client import HrdbClient

logger = logging.getLogger(__name__)


def get_hrdb_client() -> HrdbClient:
    """Secrets Managerから認証情報を取得してHrdbClientを生成する."""
    secret_id = os.environ["GAMBLE_OS_SECRET_ID"]
    client = boto3.client("secretsmanager", region_name="ap-northeast-1")
    secret = json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])
    return HrdbClient(
        club_id=secret["club_id"],
        club_password=secret["club_password"],
        api_domain=secret["api_domain"],
    )
