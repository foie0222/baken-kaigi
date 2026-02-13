"""競馬AIナビ スクレイピング Lambda.

horse-racing-ai-navi.com から競馬AIナビの予想指数を取得し、DynamoDBに保存する。

サイト構造:
- /ai-keiba-yosou ページに全レースの予想データが掲載
- データはscriptタグ内およびid="dual-index-report-data"要素にJSON形式で埋め込み
- JSON構造: {"YYYYMMDD": [race1, race2, ...]}
- 各レース: {keibajo_code, keibajo_name, race_bango, horses: [...]}
- 各馬: {umaban, umamei, tansho_index, fukusho_index, kitaichi_index, ability_index_old, ...}
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
import requests
from bs4 import BeautifulSoup

from batch.ai_shisu_scraper import VENUE_CODE_MAP
from batch.dynamodb_utils import convert_floats

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 定数
BASE_URL = "https://horse-racing-ai-navi.com"
SOURCE_NAME = "keiba-ai-navi"
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 1.0  # サーバー負荷軽減のための遅延

# タイムゾーン
JST = timezone(timedelta(hours=9))


def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("AI_PREDICTIONS_TABLE_NAME", "baken-kaigi-ai-predictions")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def fetch_page(url: str) -> BeautifulSoup | None:
    """ページを取得してBeautifulSoupオブジェクトを返す."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BakenKaigiBot/1.0; +https://bakenkaigi.com)",
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def extract_race_data_json(soup: BeautifulSoup, target_date_str: str) -> list[dict] | None:
    """ページからレースデータJSONを抽出.

    データは以下の2箇所に格納される（同一データ）:
    1. <script> タグ内にJSON直接記述
    2. id="dual-index-report-data" のscriptタグ内

    JSON構造:
    {
        "20260208": [
            {
                "keibajo_code": "05",
                "keibajo_name": "東京",
                "race_bango": 1,
                "race_id": "05_01",
                ...
                "horses": [
                    {
                        "umaban": 1,
                        "umamei": "シュートザムーン",
                        "tansho_index": 0.7,
                        "fukusho_index": 3.3,
                        "kitaichi_index": -41,
                        "ability_index_old": 4,
                        ...
                    }, ...
                ]
            }, ...
        ]
    }

    Args:
        soup: ページのBeautifulSoup
        target_date_str: 対象日付 (例: "20260208")

    Returns:
        list[dict] | None: レースデータのリスト、またはNone
    """
    # id="dual-index-report-data" を優先的に探す
    data_elem = soup.find(id="dual-index-report-data")
    if data_elem:
        try:
            json_text = data_elem.get_text(strip=True)
            data = json.loads(json_text)
            if target_date_str in data:
                return data[target_date_str]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse dual-index-report-data: {e}")

    # フォールバック: scriptタグ内のJSONを探す
    for script in soup.find_all("script"):
        text = script.get_text()
        if target_date_str not in text or "keibajo_code" not in text:
            continue

        # JSONが巨大なため、正規表現では限界がある
        # 代わりにJSON開始位置を見つけて手動パース
        json_start = text.find(f'{{"{target_date_str}":[')
        if json_start < 0:
            continue

        # JSONの終了位置を見つける（ブラケットの深さを追跡）
        try:
            data = _extract_json_from_position(text, json_start)
            if data and target_date_str in data:
                return data[target_date_str]
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON from script: {e}")

    return None


def _extract_json_from_position(text: str, start: int) -> dict | None:
    """テキストの指定位置からJSONオブジェクトを抽出.

    波括弧の深さを追跡して、完全なJSONオブジェクトを切り出す。

    Args:
        text: テキスト全体
        start: JSON開始位置

    Returns:
        dict | None: パースされたJSONオブジェクト
    """
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        c = text[i]

        if escape_next:
            escape_next = False
            continue

        if c == "\\":
            escape_next = True
            continue

        if c == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                json_str = text[start : i + 1]
                return json.loads(json_str)

    return None


def parse_race_predictions(race_data: dict) -> list[dict]:
    """レースデータからAI予想を抽出.

    各馬のデータからtansho_index（単勝指数）をスコアとして使用する。
    tansho_indexは勝率（%）で、値が大きいほど高評価。

    Args:
        race_data: レースの辞書データ（horsesキーを含む）

    Returns:
        list of dict: [{"rank": 1, "score": 17.1, "horse_number": 14, "horse_name": "xxx"}, ...]
    """
    predictions = []
    horses = race_data.get("horses", [])

    for horse in horses:
        try:
            umaban = horse.get("umaban")
            umamei = horse.get("umamei", "")
            tansho_index = horse.get("tansho_index")

            if umaban is None or tansho_index is None or not umamei:
                continue

            horse_number = int(umaban)
            score = float(tansho_index)

            if 1 <= horse_number <= 18:
                predictions.append({
                    "score": round(score, 1),
                    "horse_number": horse_number,
                    "horse_name": umamei,
                    # 追加指数も保存
                    "fukusho_index": round(float(horse.get("fukusho_index", 0)), 1),
                    "kitaichi_index": int(horse.get("kitaichi_index", 0)),
                })
        except (ValueError, TypeError):
            continue

    # スコア降順でソートしてランク付け
    predictions.sort(key=lambda x: x["score"], reverse=True)
    for i, pred in enumerate(predictions):
        pred["rank"] = i + 1

    return predictions


def generate_race_id(date_str: str, venue: str, race_number: int) -> str:
    """JRA-VANスタイルのrace_idを生成.

    Args:
        date_str: 日付文字列 (例: "20260208")
        venue: 競馬場名 (例: "東京")
        race_number: レース番号 (例: 11)

    Returns:
        str: race_id (例: "20260208_05_11")
    """
    venue_code = VENUE_CODE_MAP.get(venue, "00")
    return f"{date_str}_{venue_code}_{race_number:02d}"


def save_predictions(
    table,
    race_id: str,
    venue: str,
    race_number: int,
    predictions: list[dict],
    scraped_at: datetime,
) -> None:
    """予想データをDynamoDBに保存."""
    # TTL計算（7日後）
    ttl = int((scraped_at + timedelta(days=TTL_DAYS)).timestamp())

    item = {
        "race_id": race_id,
        "source": SOURCE_NAME,
        "venue": venue,
        "race_number": race_number,
        "predictions": convert_floats(predictions),
        "scraped_at": scraped_at.isoformat(),
        "ttl": ttl,
    }

    table.put_item(Item=item)
    logger.info(f"Saved predictions for {race_id}: {len(predictions)} horses")


def scrape_races() -> dict[str, Any]:
    """メインのスクレイピング処理.

    前日夜に翌日分のAI予想を取得する。
    horse-racing-ai-navi.com の /ai-keiba-yosou ページにアクセスし、
    埋め込みJSONから翌日の全レースデータを取得する。

    フロー:
    1. /ai-keiba-yosou ページを取得
    2. 埋め込みJSONから翌日のレースデータを抽出
    3. 各レースの馬データをパースしてDynamoDBに保存

    Returns:
        dict: {"success": bool, "races_scraped": int, "errors": list}
    """
    table = get_dynamodb_table()
    scraped_at = datetime.now(JST)
    tomorrow = scraped_at + timedelta(days=1)
    date_str = tomorrow.strftime("%Y%m%d")

    results = {
        "success": True,
        "races_scraped": 0,
        "errors": [],
    }

    # Step 1: 予想ページを取得
    predict_url = f"{BASE_URL}/ai-keiba-yosou"
    logger.info(f"Fetching prediction page: {predict_url}")
    soup = fetch_page(predict_url)
    if not soup:
        results["success"] = False
        results["errors"].append("Failed to fetch prediction page")
        return results

    # Step 2: 埋め込みJSONからレースデータを抽出
    race_data_list = extract_race_data_json(soup, date_str)
    if not race_data_list:
        # 開催がない日は正常終了扱い
        logger.info(f"No race data found for {date_str}")
        results["races_scraped"] = 0
        return results

    logger.info(f"Found {len(race_data_list)} races for {date_str}")

    # Step 3: 各レースの予想データをパースして保存
    for race_data in race_data_list:
        keibajo_name = race_data.get("keibajo_name", "")
        race_bango = race_data.get("race_bango")

        # JRA中央競馬場のみ対象
        if keibajo_name not in VENUE_CODE_MAP:
            continue

        if race_bango is None:
            continue

        race_number = int(race_bango)
        predictions = parse_race_predictions(race_data)

        if not predictions:
            results["errors"].append(f"No predictions for {keibajo_name} {race_number}R")
            continue

        race_id = generate_race_id(date_str, keibajo_name, race_number)

        try:
            save_predictions(
                table=table,
                race_id=race_id,
                venue=keibajo_name,
                race_number=race_number,
                predictions=predictions,
                scraped_at=scraped_at,
            )
            results["races_scraped"] += 1
        except Exception as e:
            logger.error(f"Failed to save {race_id}: {e}")
            results["errors"].append(f"Failed to save {race_id}: {str(e)}")

    if results["errors"]:
        results["success"] = results["races_scraped"] > 0

    return results


def handler(event: dict, context: Any) -> dict:
    """Lambda ハンドラー.

    Args:
        event: Lambda イベント
        context: Lambda コンテキスト

    Returns:
        dict: 実行結果
    """
    logger.info(f"Starting keiba-ai-navi scraper: event={event}")

    try:
        results = scrape_races()
        logger.info(f"Scraping completed: {results}")

        return {
            "statusCode": 200 if results["success"] else 500,
            "body": results,
        }
    except Exception as e:
        logger.exception(f"Scraper failed: {e}")
        return {
            "statusCode": 500,
            "body": {
                "success": False,
                "error": str(e),
            },
        }
