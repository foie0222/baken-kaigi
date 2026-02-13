"""HRDB レース結果更新バッチ.

EventBridge → Lambda で毎週月曜6:00 JSTに実行。
HRDB-APIからRACEDTLの確定結果を取得し、DynamoDBのrunnersテーブルを更新する。
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


def _get_last_week_range() -> tuple[str, str]:
    """前週の月曜〜日曜の日付範囲を返す."""
    today = datetime.now(JST)
    # 今週月曜からの差分
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    return last_monday.strftime("%Y%m%d"), last_sunday.strftime("%Y%m%d")


def handler(event: dict, context) -> dict:
    """レース結果更新ハンドラー."""
    from_date = event.get("from_date")
    to_date = event.get("to_date")
    if not from_date or not to_date:
        from_date, to_date = _get_last_week_range()

    logger.info("Fetching results for %s - %s", from_date, to_date)

    hrdb_client = get_hrdb_client()
    rows = hrdb_client.query(
        f"SELECT * FROM RACEDTL WHERE OPDT BETWEEN '{from_date}' AND '{to_date}' AND KAKUTEI > 0"
    )

    table_name = os.environ["RUNNERS_TABLE_NAME"]
    table = boto3.resource("dynamodb", region_name="ap-northeast-1").Table(table_name)

    with table.batch_writer() as batch:
        for row in rows:
            item = map_racedtl_to_runner_item(row)
            batch.put_item(Item=item)

    logger.info("Updated %d results in %s", len(rows), table_name)
    return {"status": "ok", "count": len(rows)}
