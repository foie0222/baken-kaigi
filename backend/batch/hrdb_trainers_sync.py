"""HRDB 調教師マスタ同期バッチ.

runnersテーブルから調教師IDを収集し、trainersテーブルに未登録のものをHRDBから取得する。
"""
import logging
import os

import boto3

from batch.hrdb_common import get_hrdb_client
from src.infrastructure.clients.hrdb_mapper import map_trnr_to_trainer_item

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_IDS_PER_QUERY = 500


def _get_missing_trainer_ids(
    runners_table, trainers_table,
) -> list[str]:
    """runnersにあってtrainersにないtrainer_idを返す."""
    runner_ids = set()
    response = runners_table.scan(ProjectionExpression="trainer_id")
    runner_ids.update(
        item["trainer_id"]
        for item in response.get("Items", [])
        if item.get("trainer_id")
    )
    while response.get("LastEvaluatedKey"):
        response = runners_table.scan(
            ProjectionExpression="trainer_id",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        runner_ids.update(
            item["trainer_id"]
            for item in response.get("Items", [])
            if item.get("trainer_id")
        )

    existing_ids = set()
    for trainer_id in runner_ids:
        resp = trainers_table.get_item(
            Key={"trainer_id": trainer_id, "sk": "info"},
            ProjectionExpression="trainer_id",
        )
        if resp.get("Item"):
            existing_ids.add(trainer_id)

    return list(runner_ids - existing_ids)


def handler(event: dict, context) -> dict:
    """調教師マスタ同期ハンドラー."""
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    runners_table = dynamodb.Table(
        os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners")
    )
    trainers_table = dynamodb.Table(
        os.environ.get("TRAINERS_TABLE_NAME", "baken-kaigi-trainers")
    )

    missing_ids = _get_missing_trainer_ids(runners_table, trainers_table)
    if not missing_ids:
        logger.info("No missing trainers to sync")
        return {"status": "ok", "count": 0}

    logger.info("Found %d missing trainers", len(missing_ids))

    hrdb_client = get_hrdb_client()
    total_synced = 0

    for i in range(0, len(missing_ids), MAX_IDS_PER_QUERY):
        chunk = missing_ids[i : i + MAX_IDS_PER_QUERY]
        for id_ in chunk:
            if not id_.isalnum():
                logger.warning("Skipping invalid trainer_id: %s", id_)
                chunk = [c for c in chunk if c.isalnum()]
                break
        if not chunk:
            continue
        in_clause = ", ".join(f"'{id_}'" for id_ in chunk)
        rows = hrdb_client.query(
            f"SELECT * FROM TRNR WHERE TRNRCD IN ({in_clause})"
        )

        with trainers_table.batch_writer() as batch:
            for row in rows:
                item = map_trnr_to_trainer_item(row)
                batch.put_item(Item=item)
                total_synced += 1

    logger.info("Synced %d trainers", total_synced)
    return {"status": "ok", "count": total_synced}
