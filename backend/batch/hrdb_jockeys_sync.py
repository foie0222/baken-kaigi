"""HRDB 騎手マスタ同期バッチ.

runnersテーブルから騎手IDを収集し、jockeysテーブルに未登録のものをHRDBから取得する。
"""
import logging
import os

import boto3

from batch.hrdb_common import get_hrdb_client
from src.infrastructure.clients.hrdb_mapper import map_jky_to_jockey_item

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_IDS_PER_QUERY = 500


def _get_missing_jockey_ids(
    runners_table, jockeys_table,
) -> list[str]:
    """runnersにあってjockeysにないjockey_idを返す."""
    runner_ids = set()
    response = runners_table.scan(ProjectionExpression="jockey_id")
    runner_ids.update(
        item["jockey_id"]
        for item in response.get("Items", [])
        if item.get("jockey_id")
    )
    while response.get("LastEvaluatedKey"):
        response = runners_table.scan(
            ProjectionExpression="jockey_id",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        runner_ids.update(
            item["jockey_id"]
            for item in response.get("Items", [])
            if item.get("jockey_id")
        )

    existing_ids = set()
    for jockey_id in runner_ids:
        resp = jockeys_table.get_item(
            Key={"jockey_id": jockey_id, "sk": "info"},
            ProjectionExpression="jockey_id",
        )
        if resp.get("Item"):
            existing_ids.add(jockey_id)

    return list(runner_ids - existing_ids)


def handler(event: dict, context) -> dict:
    """騎手マスタ同期ハンドラー."""
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    runners_table = dynamodb.Table(
        os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners")
    )
    jockeys_table = dynamodb.Table(
        os.environ.get("JOCKEYS_TABLE_NAME", "baken-kaigi-jockeys")
    )

    missing_ids = _get_missing_jockey_ids(runners_table, jockeys_table)
    if not missing_ids:
        logger.info("No missing jockeys to sync")
        return {"status": "ok", "count": 0}

    logger.info("Found %d missing jockeys", len(missing_ids))

    hrdb_client = get_hrdb_client()
    total_synced = 0

    for i in range(0, len(missing_ids), MAX_IDS_PER_QUERY):
        chunk = [id_ for id_ in missing_ids[i : i + MAX_IDS_PER_QUERY] if id_.isalnum()]
        if not chunk:
            continue
        in_clause = ", ".join(f"'{id_}'" for id_ in chunk)
        rows = hrdb_client.query(
            f"SELECT * FROM JKY WHERE JKYCD IN ({in_clause})"
        )

        with jockeys_table.batch_writer() as batch:
            for row in rows:
                item = map_jky_to_jockey_item(row)
                batch.put_item(Item=item)
                total_synced += 1

    logger.info("Synced %d jockeys", total_synced)
    return {"status": "ok", "count": total_synced}
