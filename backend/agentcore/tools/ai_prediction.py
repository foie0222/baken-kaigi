"""AI予想データ取得ツール.

外部AI予想サービス（ai-shisu.com等）からスクレイピングしたデータをDynamoDBから取得する。
"""

import os

import boto3
from botocore.exceptions import ClientError
from strands import tool

# AWSリージョン（AgentCore環境ではAWS_REGION未設定の場合があるため明示指定）
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")


def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("AI_PREDICTIONS_TABLE_NAME", "baken-kaigi-ai-predictions")
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(table_name)


def _analyze_consensus(sources: list[dict]) -> dict:
    """複数ソースのコンセンサスを分析する.

    Args:
        sources: [{"source": "ai-shisu", "predictions": [...]}, ...]

    Returns:
        dict: {
            "agreed_top3": [8, 3],  # 両方のtop3に含まれる馬番
            "consensus_level": "部分合意",
            "divergence_horses": [
                {"horse_number": 5, "ranks": {"ai-shisu": 2, "muryou-keiba-ai": 8}, "gap": 6}
            ]
        }
    """
    # 各ソースのtop3馬番セットを取得
    top3_sets = []
    for s in sources:
        preds = s.get("predictions", [])
        top3 = {p["horse_number"] for p in preds[:3]}
        top3_sets.append(top3)

    # 全ソースのtop3に共通する馬番
    agreed_top3 = list(top3_sets[0].intersection(*top3_sets[1:]))

    # コンセンサスレベル判定
    common_count = len(agreed_top3)
    if common_count == 3:
        # top3の顔ぶれが一致 → 順位差を確認
        all_within_1 = True
        for horse_num in agreed_top3:
            ranks = []
            for s in sources:
                for p in s["predictions"][:3]:
                    if p["horse_number"] == horse_num:
                        ranks.append(p["rank"])
                        break
            if max(ranks) - min(ranks) > 1:
                all_within_1 = False
                break
        consensus_level = "完全合意" if all_within_1 else "概ね合意"
    elif common_count == 2:
        consensus_level = "部分合意"
    else:
        consensus_level = "大きな乖離"

    # 乖離馬の検出: 全ソースに登場する馬で順位差が3以上
    # 各ソースの馬番→順位マップを作成
    rank_maps = {}
    for s in sources:
        source_name = s["source"]
        rank_maps[source_name] = {}
        for p in s.get("predictions", []):
            rank_maps[source_name][p["horse_number"]] = p["rank"]

    # 全ソースに登場する馬番を取得
    all_source_names = list(rank_maps.keys())
    all_horses = set(rank_maps[all_source_names[0]].keys())
    for sn in all_source_names[1:]:
        all_horses &= set(rank_maps[sn].keys())

    divergence_horses = []
    for horse_num in all_horses:
        ranks_dict = {sn: rank_maps[sn][horse_num] for sn in all_source_names}
        rank_values = list(ranks_dict.values())
        gap = max(rank_values) - min(rank_values)
        if gap >= 3:
            divergence_horses.append({
                "horse_number": horse_num,
                "ranks": ranks_dict,
                "gap": gap,
            })

    divergence_horses.sort(key=lambda h: h["gap"], reverse=True)

    return {
        "agreed_top3": agreed_top3,
        "consensus_level": consensus_level,
        "divergence_horses": divergence_horses,
    }


def _get_single_source(table, race_id: str, source: str) -> dict:
    """単一ソースのAI予想データを取得する（後方互換）."""
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


def _get_all_sources(table, race_id: str) -> dict:
    """全ソースのAI予想データを取得しコンセンサス分析を付加する."""
    from boto3.dynamodb.conditions import Key

    response = table.query(
        KeyConditionExpression=Key("race_id").eq(race_id),
    )

    items = response.get("Items", [])
    if not items:
        return {
            "race_id": race_id,
            "error": "AI予想データが見つかりません。このレースのデータはまだ取得されていないか、対象外のレースです。",
            "sources": [],
        }

    sources = []
    for item in items:
        item.pop("ttl", None)
        sources.append({
            "source": item.get("source"),
            "venue": item.get("venue"),
            "race_number": item.get("race_number"),
            "predictions": item.get("predictions", []),
            "scraped_at": item.get("scraped_at"),
        })

    result = {
        "race_id": race_id,
        "sources": sources,
    }

    # 2ソース以上ある場合のみコンセンサス分析を付加
    if len(sources) >= 2:
        result["consensus"] = _analyze_consensus(sources)

    return result


@tool
def get_ai_prediction(race_id: str, source: str | None = None) -> dict:
    """外部AIサービスの予想指数を取得する.

    ai-shisu.com等の外部AI予想サービスから取得したデータを返す。
    このデータは毎朝自動でスクレイピングされ、DynamoDBに保存されている。

    Args:
        race_id: レースID (例: "20260131_05_11")
        source: データソース名。Noneの場合は全ソースを取得しコンセンサス分析を付加。
                指定した場合は従来通り単一ソースを返す。

    Returns:
        dict: AI予想データ
            source指定時（後方互換）:
                - race_id: レースID
                - source: データソース
                - venue: 競馬場名
                - race_number: レース番号
                - predictions: 予想リスト
                - scraped_at: スクレイピング日時
                - error: エラーメッセージ（取得失敗時）
            source=None（全ソース取得）:
                - race_id: レースID
                - sources: ソース別予想データリスト
                - consensus: コンセンサス分析（2ソース以上の場合のみ）
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
                "predictions": [],
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
                "predictions": [],
            }
        else:
            return {
                "race_id": race_id,
                "error": f"予期しないエラー: {str(e)}",
                "sources": [],
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

        # 競馬場名→レース番号の順でソート
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
