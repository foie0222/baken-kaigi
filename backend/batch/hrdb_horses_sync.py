"""HRDB 馬マスタ同期バッチ.

runnersテーブルから馬IDを収集し、horsesテーブルに未登録のものをHRDBから取得する。
"""
import logging
import os

import boto3

from batch.hrdb_common import get_hrdb_client
from src.infrastructure.clients.hrdb_mapper import map_horse_to_horse_item

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_IDS_PER_QUERY = 500


def _get_missing_horse_ids(
    runners_table, horses_table,
) -> list[str]:
    """runnersにあってhorsesにないhorse_idを返す."""
    # runnersから全horse_idを収集
    runner_ids = set()
    response = runners_table.scan(ProjectionExpression="horse_id")
    runner_ids.update(
        item["horse_id"] for item in response.get("Items", []) if item.get("horse_id")
    )
    while response.get("LastEvaluatedKey"):
        response = runners_table.scan(
            ProjectionExpression="horse_id",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        runner_ids.update(
            item["horse_id"]
            for item in response.get("Items", [])
            if item.get("horse_id")
        )

    # horsesテーブルに既存のIDを除外
    existing_ids = set()
    for horse_id in runner_ids:
        resp = horses_table.get_item(
            Key={"horse_id": horse_id, "sk": "info"},
            ProjectionExpression="horse_id",
        )
        if resp.get("Item"):
            existing_ids.add(horse_id)

    return list(runner_ids - existing_ids)


def handler(event: dict, context) -> dict:
    """馬マスタ同期ハンドラー."""
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    runners_table = dynamodb.Table(
        os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners")
    )
    horses_table = dynamodb.Table(
        os.environ.get("HORSES_TABLE_NAME", "baken-kaigi-horses")
    )

    missing_ids = _get_missing_horse_ids(runners_table, horses_table)
    if not missing_ids:
        logger.info("No missing horses to sync")
        return {"status": "ok", "count": 0}

    logger.info("Found %d missing horses", len(missing_ids))

    hrdb_client = get_hrdb_client()
    total_synced = 0

    for i in range(0, len(missing_ids), MAX_IDS_PER_QUERY):
        chunk = [id_ for id_ in missing_ids[i : i + MAX_IDS_PER_QUERY] if id_.isalnum()]
        if not chunk:
            continue
        in_clause = ", ".join(f"'{id_}'" for id_ in chunk)
        rows = hrdb_client.query(
            f"SELECT * FROM HORSE WHERE BLDNO IN ({in_clause})"
        )

        with horses_table.batch_writer() as batch:
            for row in rows:
                item = map_horse_to_horse_item(row)
                batch.put_item(Item=item)
                total_synced += 1

    logger.info("Synced %d horses", total_synced)
    return {"status": "ok", "count": total_synced}
