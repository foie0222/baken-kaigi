"""HRDB 出走馬取得バッチ.

EventBridge → Lambda で毎晩21:00 JST + 当日朝8:00 JST に実行。
HRDB-APIからRACEDTLを取得し、DynamoDBのrunnersテーブルに書き込む。
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3

from batch.hrdb_common import get_hrdb_client
from src.infrastructure.clients.hrdb_mapper import map_racedtl_to_runner_item

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JST = timezone(timedelta(hours=9))


def _get_hrdb_client():
    return get_hrdb_client()


def handler(event: dict, context) -> dict:
    """出走馬データ取得ハンドラー."""
    target_date = event.get("target_date")
    if not target_date:
        offset_days = event.get("offset_days", 1)
        dt = datetime.now(JST) + timedelta(days=offset_days)
        target_date = dt.strftime("%Y%m%d")

    logger.info("Fetching runners for date: %s", target_date)

    hrdb_client = _get_hrdb_client()
    rows = hrdb_client.query(
        f"SELECT * FROM RACEDTL WHERE OPDT = '{target_date}'"
    )

    table_name = os.environ["RUNNERS_TABLE_NAME"]
    table = boto3.resource("dynamodb", region_name="ap-northeast-1").Table(table_name)

    with table.batch_writer() as batch:
        for row in rows:
            item = map_racedtl_to_runner_item(row)
            batch.put_item(Item=item)

    logger.info("Wrote %d runners to %s", len(rows), table_name)
    return {"status": "ok", "count": len(rows)}
