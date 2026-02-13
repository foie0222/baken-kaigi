"""HRDB レース取得バッチ.

EventBridge → Lambda で毎晩21:00 JST + 当日朝8:00 JST に実行。
HRDB-APIからRACEMSTを取得し、DynamoDBのracesテーブルに書き込む。
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3

from src.infrastructure.clients.hrdb_client import HrdbClient
from src.infrastructure.clients.hrdb_mapper import map_racemst_to_race_item

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JST = timezone(timedelta(hours=9))


def _get_hrdb_client() -> HrdbClient:
    secret_id = os.environ["GAMBLE_OS_SECRET_ID"]
    client = boto3.client("secretsmanager", region_name="ap-northeast-1")
    secret = json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])
    return HrdbClient(
        club_id=secret["club_id"],
        club_password=secret["club_password"],
        api_domain=secret["api_domain"],
    )


def handler(event: dict, context) -> dict:
    """レースデータ取得ハンドラー."""
    target_date = event.get("target_date")
    if not target_date:
        offset_days = event.get("offset_days", 1)
        dt = datetime.now(JST) + timedelta(days=offset_days)
        target_date = dt.strftime("%Y%m%d")

    logger.info("Fetching races for date: %s", target_date)

    hrdb_client = _get_hrdb_client()
    rows = hrdb_client.query(
        f"SELECT * FROM RACEMST WHERE OPDT = '{target_date}'"
    )

    table_name = os.environ["RACES_TABLE_NAME"]
    table = boto3.resource("dynamodb", region_name="ap-northeast-1").Table(table_name)

    with table.batch_writer() as batch:
        for row in rows:
            item = map_racemst_to_race_item(row)
            batch.put_item(Item=item)

    logger.info("Wrote %d races to %s", len(rows), table_name)
    return {"status": "ok", "count": len(rows)}
