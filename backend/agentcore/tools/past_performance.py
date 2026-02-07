"""馬柱（過去成績）データ取得ツール.

外部サービスからスクレイピングした馬柱データをDynamoDBから取得する。
"""

import os

import boto3
from botocore.exceptions import ClientError
from strands import tool

# AWSリージョン（AgentCore環境ではAWS_REGION未設定の場合があるため明示指定）
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")


def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("PAST_PERFORMANCES_TABLE_NAME", "baken-kaigi-past-performances")
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(table_name)


def _get_single_source(table, race_id: str, source: str) -> dict:
    """単一ソースの馬柱データを取得する."""
    response = table.get_item(
        Key={
            "race_id": race_id,
            "source": source,
        }
    )

    item = response.get("Item")
    if not item:
        return {
            "race_id": race_id,
            "source": source,
            "error": f"馬柱データが見つかりません。このレースの{source}データはまだ取得されていないか、対象外のレースです。",
            "horses": [],
        }

    # TTL属性は返さない
    item.pop("ttl", None)

    return {
        "race_id": item.get("race_id"),
        "source": item.get("source"),
        "venue": item.get("venue"),
        "race_number": item.get("race_number"),
        "horses": item.get("horses", []),
        "scraped_at": item.get("scraped_at"),
    }


def _get_all_sources(table, race_id: str) -> dict:
    """全ソースの馬柱データを取得する."""
    from boto3.dynamodb.conditions import Key

    response = table.query(
        KeyConditionExpression=Key("race_id").eq(race_id),
    )

    items = response.get("Items", [])
    if not items:
        return {
            "race_id": race_id,
            "error": "馬柱データが見つかりません。このレースのデータはまだ取得されていないか、対象外のレースです。",
            "sources": [],
        }

    sources = []
    for item in items:
        item.pop("ttl", None)
        sources.append({
            "source": item.get("source"),
            "venue": item.get("venue"),
            "race_number": item.get("race_number"),
            "horses": item.get("horses", []),
            "scraped_at": item.get("scraped_at"),
        })

    return {
        "race_id": race_id,
        "sources": sources,
    }


@tool
def get_past_performance(race_id: str, source: str | None = None) -> dict:
    """馬柱（過去成績）データを取得する.

    外部サービスからスクレイピングした馬柱データをDynamoDBから取得する。
    各出走馬の近5走成績、血統情報を含む。

    Args:
        race_id: レースID (例: "20260131_05_11")
        source: データソース名。Noneの場合は全ソースを取得。
                利用可能ソース: "keibagrant"

    Returns:
        dict: 馬柱データ
            source指定時:
                - race_id: レースID
                - source: データソース
                - venue: 競馬場名
                - race_number: レース番号
                - horses: 出走馬リスト
                    - horse_number: 馬番
                    - horse_name: 馬名
                    - past_races: 近走成績リスト
                        - date, venue, race_name, distance, track,
                          finish_position, time, weight, jockey
                    - sire: 父馬名
                    - dam: 母馬名
                    - dam_sire: 母父馬名
                - scraped_at: スクレイピング日時
                - error: エラーメッセージ（取得失敗時）
            source=None（全ソース取得）:
                - race_id: レースID
                - sources: ソース別馬柱データリスト
    """
    try:
        table = get_dynamodb_table()

        if source is not None:
            return _get_single_source(table, race_id, source)
        else:
            return _get_all_sources(table, race_id)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if source is not None:
            return {
                "race_id": race_id,
                "source": source,
                "error": f"DynamoDBエラー: {error_code}",
                "horses": [],
            }
        else:
            return {
                "race_id": race_id,
                "error": f"DynamoDBエラー: {error_code}",
                "sources": [],
            }
    except Exception as e:
        if source is not None:
            return {
                "race_id": race_id,
                "source": source,
                "error": f"予期しないエラー: {str(e)}",
                "horses": [],
            }
        else:
            return {
                "race_id": race_id,
                "error": f"予期しないエラー: {str(e)}",
                "sources": [],
            }
