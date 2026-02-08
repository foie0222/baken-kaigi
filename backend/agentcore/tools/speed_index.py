"""スピード指数データ取得ツール.

外部スピード指数サービスからスクレイピングしたデータをDynamoDBから取得する。
"""

import os

import boto3
from botocore.exceptions import ClientError
from strands import tool

# AWSリージョン（AgentCore環境ではAWS_REGION未設定の場合があるため明示指定）
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")


def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("SPEED_INDICES_TABLE_NAME", "baken-kaigi-speed-indices")
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(table_name)


def _analyze_consensus(sources: list[dict]) -> dict:
    """複数ソースのコンセンサスを分析する.

    Args:
        sources: [{"source": "jiro8-speed", "indices": [...]}, ...]

    Returns:
        dict: {
            "agreed_top3": [8, 3],  # 両方のtop3に含まれる馬番
            "consensus_level": "部分合意",
            "divergence_horses": [
                {"horse_number": 5, "ranks": {"jiro8-speed": 2, "kichiuma-speed": 8}, "gap": 6}
            ]
        }
    """
    # 各ソースのtop3馬番セットを取得
    top3_sets = []
    for s in sources:
        indices = s.get("indices", [])
        top3 = {i["horse_number"] for i in indices[:3]}
        top3_sets.append(top3)

    # 全ソースのtop3に共通する馬番（先頭ソースの順位でソートして順序安定化）
    first_source_ranks = {
        i["horse_number"]: i["rank"] for i in sources[0].get("indices", [])
    }
    agreed_set = top3_sets[0].intersection(*top3_sets[1:])
    agreed_top3 = sorted(
        agreed_set,
        key=lambda hn: (first_source_ranks.get(hn, float("inf")), hn),
    )

    # コンセンサスレベル判定
    common_count = len(agreed_top3)
    if common_count == 3:
        # top3の顔ぶれが一致 → 各ソースのtop3順位（並び）が完全一致か確認
        base_top3 = [i["horse_number"] for i in sources[0].get("indices", [])[:3]]
        top3_order_all_match = all(
            [i["horse_number"] for i in s.get("indices", [])[:3]] == base_top3
            for s in sources[1:]
        )
        consensus_level = "完全合意" if top3_order_all_match else "概ね合意"
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
        for i in s.get("indices", []):
            rank_maps[source_name][i["horse_number"]] = i["rank"]

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
    """単一ソースのスピード指数データを取得する."""
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
            "error": f"スピード指数データが見つかりません。このレースの{source}データはまだ取得されていないか、対象外のレースです。",
            "indices": [],
        }

    # TTL属性は返さない
    item.pop("ttl", None)

    return {
        "race_id": item.get("race_id"),
        "source": item.get("source"),
        "venue": item.get("venue"),
        "race_number": item.get("race_number"),
        "indices": item.get("indices", []),
        "scraped_at": item.get("scraped_at"),
    }


def _get_all_sources(table, race_id: str) -> dict:
    """全ソースのスピード指数データを取得しコンセンサス分析を付加する."""
    from boto3.dynamodb.conditions import Key

    response = table.query(
        KeyConditionExpression=Key("race_id").eq(race_id),
    )

    items = response.get("Items", [])
    if not items:
        return {
            "race_id": race_id,
            "error": "スピード指数データが見つかりません。このレースのデータはまだ取得されていないか、対象外のレースです。",
            "sources": [],
        }

    sources = []
    for item in items:
        item.pop("ttl", None)
        sources.append({
            "source": item.get("source"),
            "venue": item.get("venue"),
            "race_number": item.get("race_number"),
            "indices": item.get("indices", []),
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
def get_speed_index(race_id: str, source: str | None = None) -> dict:
    """スピード指数データを取得する.

    外部スピード指数サービスからスクレイピングしたデータをDynamoDBから取得する。

    Args:
        race_id: レースID (例: "20260131_05_11")
        source: データソース名。Noneの場合は全ソースを取得しコンセンサス分析を付加。
                指定した場合は単一ソースを返す。
                利用可能ソース: "jiro8-speed", "kichiuma-speed", "daily-speed"

    Returns:
        dict: スピード指数データ
            source指定時:
                - race_id: レースID
                - source: データソース
                - venue: 競馬場名
                - race_number: レース番号
                - indices: スピード指数リスト
                - scraped_at: スクレイピング日時
                - error: エラーメッセージ（取得失敗時）
            source=None（全ソース取得）:
                - race_id: レースID
                - sources: ソース別スピード指数データリスト
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
                "indices": [],
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
                "indices": [],
            }
        else:
            return {
                "race_id": race_id,
                "error": f"予期しないエラー: {str(e)}",
                "sources": [],
            }


@tool
def list_speed_indices_for_date(date: str, source: str = "jiro8-speed") -> dict:
    """指定日のスピード指数データ一覧を取得する.

    Args:
        date: 日付 (例: "20260131")
        source: データソース名 (デフォルト: "jiro8-speed")

    Returns:
        dict: スピード指数データ一覧
            - date: 日付
            - source: データソース
            - races: レース一覧
                - race_id: レースID
                - venue: 競馬場名
                - race_number: レース番号
                - top_indices: 上位3頭のスピード指数
            - error: エラーメッセージ（取得失敗時）
    """
    try:
        table = get_dynamodb_table()

        # 日付プレフィックスでスキャン（race_idは日付で始まる）
        # LastEvaluatedKeyでページネーションし全件取得
        items = []
        scan_kwargs = {
            "FilterExpression": "begins_with(race_id, :date) AND #src = :source",
            "ExpressionAttributeNames": {
                "#src": "source",
            },
            "ExpressionAttributeValues": {
                ":date": date,
                ":source": source,
            },
        }

        while True:
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        races = []
        for item in items:
            indices = item.get("indices", [])
            top_indices = indices[:3] if indices else []

            races.append({
                "race_id": item.get("race_id"),
                "venue": item.get("venue"),
                "race_number": item.get("race_number"),
                "top_indices": top_indices,
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
