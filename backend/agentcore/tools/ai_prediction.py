"""AI予想データ取得ツール.

外部AI予想サービス（ai-shisu.com等）からスクレイピングしたデータをDynamoDBから取得する。
"""

import os

import boto3
from botocore.exceptions import ClientError
from strands import tool


def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("AI_PREDICTIONS_TABLE_NAME", "baken-kaigi-ai-predictions")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


@tool
def get_ai_prediction(race_id: str, source: str = "ai-shisu") -> dict:
    """外部AIサービスの予想指数を取得する.

    ai-shisu.com等の外部AI予想サービスから取得したデータを返す。
    このデータは毎朝自動でスクレイピングされ、DynamoDBに保存されている。

    Args:
        race_id: レースID (例: "20260131_05_11")
        source: データソース名 (デフォルト: "ai-shisu")

    Returns:
        dict: AI予想データ
            - race_id: レースID
            - source: データソース
            - venue: 競馬場名
            - race_number: レース番号
            - predictions: 予想リスト
                - rank: 順位
                - score: AI指数
                - horse_number: 馬番
                - horse_name: 馬名
            - scraped_at: スクレイピング日時
            - error: エラーメッセージ（取得失敗時）
    """
    try:
        table = get_dynamodb_table()

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
                "error": f"AI予想データが見つかりません。このレースの{source}データはまだ取得されていないか、対象外のレースです。",
                "predictions": [],
            }

        # TTL属性は返さない
        item.pop("ttl", None)

        return {
            "race_id": item.get("race_id"),
            "source": item.get("source"),
            "venue": item.get("venue"),
            "race_number": item.get("race_number"),
            "predictions": item.get("predictions", []),
            "scraped_at": item.get("scraped_at"),
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        return {
            "race_id": race_id,
            "source": source,
            "error": f"DynamoDBエラー: {error_code}",
            "predictions": [],
        }
    except Exception as e:
        return {
            "race_id": race_id,
            "source": source,
            "error": f"予期しないエラー: {str(e)}",
            "predictions": [],
        }


@tool
def list_ai_predictions_for_date(date: str, source: str = "ai-shisu") -> dict:
    """指定日のAI予想データ一覧を取得する.

    Args:
        date: 日付 (例: "20260131")
        source: データソース名 (デフォルト: "ai-shisu")

    Returns:
        dict: AI予想データ一覧
            - date: 日付
            - source: データソース
            - races: レース一覧
                - race_id: レースID
                - venue: 競馬場名
                - race_number: レース番号
                - top_predictions: 上位3頭の予想
            - error: エラーメッセージ（取得失敗時）
    """
    try:
        table = get_dynamodb_table()

        # 日付プレフィックスでスキャン（race_idは日付で始まる）
        response = table.scan(
            FilterExpression="begins_with(race_id, :date) AND #src = :source",
            ExpressionAttributeNames={
                "#src": "source",
            },
            ExpressionAttributeValues={
                ":date": date,
                ":source": source,
            },
        )

        items = response.get("Items", [])

        races = []
        for item in items:
            predictions = item.get("predictions", [])
            top_predictions = predictions[:3] if predictions else []

            races.append({
                "race_id": item.get("race_id"),
                "venue": item.get("venue"),
                "race_number": item.get("race_number"),
                "top_predictions": top_predictions,
            })

        # レース番号でソート
        races.sort(key=lambda x: (x.get("venue", ""), x.get("race_number", 0)))

        return {
            "date": date,
            "source": source,
            "races": races,
            "total_count": len(races),
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        return {
            "date": date,
            "source": source,
            "error": f"DynamoDBエラー: {error_code}",
            "races": [],
        }
    except Exception as e:
        return {
            "date": date,
            "source": source,
            "error": f"予期しないエラー: {str(e)}",
            "races": [],
        }
