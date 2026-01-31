"""AI指数スクレイピング Lambda.

ai-shisu.com から競馬のAI指数を取得し、DynamoDBに保存する。
"""

import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
import requests
from bs4 import BeautifulSoup

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 定数
BASE_URL = "https://ai-shisu.com"
RECENT_RACES_URL = f"{BASE_URL}/event_dates/recent_show"
SOURCE_NAME = "ai-shisu"
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 1.0  # サーバー負荷軽減のための遅延

# タイムゾーン
JST = timezone(timedelta(hours=9))

# 競馬場名からJRA-VAN競馬場コードへのマッピング
VENUE_CODE_MAP = {
    "札幌": "01",
    "函館": "02",
    "福島": "03",
    "新潟": "04",
    "東京": "05",
    "中山": "06",
    "中京": "07",
    "京都": "08",
    "阪神": "09",
    "小倉": "10",
}


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


def parse_race_list(soup: BeautifulSoup) -> list[dict]:
    """レース一覧ページからレース情報を抽出.

    Returns:
        list of dict: [{"url": "/races/xxx", "venue": "東京", "race_number": 11}, ...]
    """
    races = []

    # レースリンクを探す（/races/数字 のパターン）
    for link in soup.find_all("a", href=re.compile(r"^/races/\d+")):
        href = link.get("href", "")
        text = link.get_text(strip=True)

        # "東京 11R" のようなパターンを解析
        match = re.match(r"(.+?)\s*(\d+)R", text)
        if match:
            venue = match.group(1).strip()
            race_number = int(match.group(2))

            # JRA中央競馬場のみ対象
            if venue in VENUE_CODE_MAP:
                races.append({
                    "url": href,
                    "venue": venue,
                    "race_number": race_number,
                })

    return races


def parse_race_predictions(soup: BeautifulSoup) -> list[dict]:
    """レースページからAI指数データを抽出.

    Returns:
        list of dict: [{"rank": 1, "score": 691, "horse_number": 8, "horse_name": "xxx"}, ...]
    """
    predictions = []

    # テーブルからデータを探す
    # AI指数は「指数」「順位」などのヘッダーを持つテーブルにある
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")

        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue

            # セルのテキストを取得
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            # "1位", "691点", "8番", "馬名" のようなパターンを探す
            for i, text in enumerate(cell_texts):
                # 順位パターン（1位、2位など）
                rank_match = re.match(r"(\d+)位", text)
                if rank_match and i + 3 < len(cell_texts):
                    rank = int(rank_match.group(1))

                    # 次のセルからスコアを取得
                    score_match = re.search(r"(\d+)点?", cell_texts[i + 1])
                    # 馬番を取得
                    number_match = re.search(r"(\d+)番?", cell_texts[i + 2])

                    if score_match and number_match:
                        score = int(score_match.group(1))
                        horse_number = int(number_match.group(1))
                        horse_name = cell_texts[i + 3] if i + 3 < len(cell_texts) else ""

                        predictions.append({
                            "rank": rank,
                            "score": score,
                            "horse_number": horse_number,
                            "horse_name": horse_name,
                        })
                    break

    # 順位でソート
    predictions.sort(key=lambda x: x["rank"])

    return predictions


def generate_race_id(date_str: str, venue: str, race_number: int) -> str:
    """JRA-VANスタイルのrace_idを生成.

    Args:
        date_str: 日付文字列 (例: "20260131")
        venue: 競馬場名 (例: "東京")
        race_number: レース番号 (例: 11)

    Returns:
        str: race_id (例: "20260131_05_11")
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
        "predictions": predictions,
        "scraped_at": scraped_at.isoformat(),
        "ttl": ttl,
    }

    table.put_item(Item=item)
    logger.info(f"Saved predictions for {race_id}: {len(predictions)} horses")


def scrape_races() -> dict[str, Any]:
    """メインのスクレイピング処理.

    Returns:
        dict: {"success": bool, "races_scraped": int, "errors": list}
    """
    table = get_dynamodb_table()
    scraped_at = datetime.now(JST)
    date_str = scraped_at.strftime("%Y%m%d")

    results = {
        "success": True,
        "races_scraped": 0,
        "errors": [],
    }

    # レース一覧ページを取得
    logger.info(f"Fetching race list from {RECENT_RACES_URL}")
    soup = fetch_page(RECENT_RACES_URL)
    if not soup:
        results["success"] = False
        results["errors"].append("Failed to fetch race list page")
        return results

    # レース情報を抽出
    races = parse_race_list(soup)
    logger.info(f"Found {len(races)} races")

    if not races:
        results["errors"].append("No races found on the page")
        return results

    # 各レースのAI指数を取得
    for race_info in races:
        race_url = BASE_URL + race_info["url"]
        venue = race_info["venue"]
        race_number = race_info["race_number"]

        logger.info(f"Scraping {venue} {race_number}R: {race_url}")

        # サーバー負荷軽減のための遅延
        time.sleep(REQUEST_DELAY_SECONDS)

        race_soup = fetch_page(race_url)
        if not race_soup:
            results["errors"].append(f"Failed to fetch {venue} {race_number}R")
            continue

        predictions = parse_race_predictions(race_soup)
        if not predictions:
            results["errors"].append(f"No predictions found for {venue} {race_number}R")
            continue

        # race_id生成
        race_id = generate_race_id(date_str, venue, race_number)

        # DynamoDBに保存
        try:
            save_predictions(
                table=table,
                race_id=race_id,
                venue=venue,
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
    logger.info(f"Starting AI-Shisu scraper: event={event}")

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
