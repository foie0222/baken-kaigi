"""DynamoDB読み出しクライアント（AgentCoreツール用）.

GAMBLE-OS (HRDB-API) が投入したデータをDynamoDBから読み出す。
"""

import os

import boto3
from boto3.dynamodb.conditions import Key

_dynamodb = None


def _get_dynamodb():
    """DynamoDBリソースを取得（シングルトン）."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    return _dynamodb


def get_race(race_id: str) -> dict | None:
    """レース情報を取得する."""
    race_date = race_id.split("_")[0]
    table = _get_dynamodb().Table(
        os.environ.get("RACES_TABLE_NAME", "baken-kaigi-races"),
    )
    response = table.get_item(Key={"race_date": race_date, "race_id": race_id})
    return response.get("Item")


def get_runners(race_id: str) -> list[dict]:
    """出走馬リストを取得する."""
    table = _get_dynamodb().Table(
        os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners"),
    )
    response = table.query(KeyConditionExpression=Key("race_id").eq(race_id))
    return response.get("Items", [])


def get_horse_performances(horse_id: str, limit: int = 20) -> list[dict]:
    """馬の過去成績を取得する."""
    table = _get_dynamodb().Table(
        os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners"),
    )
    response = table.query(
        IndexName="horse_id-index",
        KeyConditionExpression=Key("horse_id").eq(horse_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return response.get("Items", [])


def get_horse(horse_id: str) -> dict | None:
    """馬情報を取得する."""
    table = _get_dynamodb().Table(
        os.environ.get("HORSES_TABLE_NAME", "baken-kaigi-horses"),
    )
    response = table.get_item(Key={"horse_id": horse_id, "sk": "info"})
    return response.get("Item")


def get_jockey(jockey_id: str) -> dict | None:
    """騎手情報を取得する."""
    table = _get_dynamodb().Table(
        os.environ.get("JOCKEYS_TABLE_NAME", "baken-kaigi-jockeys"),
    )
    response = table.get_item(Key={"jockey_id": jockey_id, "sk": "info"})
    return response.get("Item")


def get_trainer(trainer_id: str) -> dict | None:
    """調教師情報を取得する."""
    table = _get_dynamodb().Table(
        os.environ.get("TRAINERS_TABLE_NAME", "baken-kaigi-trainers"),
    )
    response = table.get_item(Key={"trainer_id": trainer_id, "sk": "info"})
    return response.get("Item")
