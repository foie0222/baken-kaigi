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
BASE_URL = "https://www.ai-shisu.com"
EVENT_DATES_URL = f"{BASE_URL}/event_dates"
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


def find_today_event_date_url(soup: BeautifulSoup, target_date: str) -> str | None:
    """開催日一覧ページから今日の日付リンクを探す.

    Args:
        soup: /event_dates ページのBeautifulSoup
        target_date: 対象日付 (例: "1/31")

    Returns:
        str | None: 日付ページURL (例: "/event_dates/2495") または None
    """
    for link in soup.find_all("a", href=re.compile(r"^/event_dates/\d+")):
        text = link.get_text(strip=True)
        # "1/31(土)" のようなパターンから日付部分を抽出
        if target_date in text:
            return link.get("href", "")
    return None


def parse_venue_list(soup: BeautifulSoup) -> list[dict]:
    """日付ページから競馬場リストを抽出.

    Returns:
        list of dict: [{"url": "/event_places/9887", "venue": "東京"}, ...]
    """
    venues = []

    for link in soup.find_all("a", href=re.compile(r"^/event_places/\d+")):
        href = link.get("href", "")
        venue = link.get_text(strip=True)

        # JRA中央競馬場のみ対象
        if venue in VENUE_CODE_MAP:
            venues.append({
                "url": href,
                "venue": venue,
            })

    return venues


def parse_race_list(soup: BeautifulSoup, venue: str) -> list[dict]:
    """競馬場ページからレース一覧を抽出.

    Args:
        soup: 競馬場ページのBeautifulSoup
        venue: 競馬場名 (例: "東京")

    Returns:
        list of dict: [{"url": "/races/xxx", "venue": "東京", "race_number": 11}, ...]
    """
    races = []

    # レースリンクを探す（/races/数字 のパターン）
    for link in soup.find_all("a", href=re.compile(r"^/races/\d+")):
        href = link.get("href", "")
        text = link.get_text(strip=True)

        # "1R 10:05" のようなパターンからレース番号を抽出
        match = re.match(r"(\d+)R", text)
        if match:
            race_number = int(match.group(1))
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

    フロー:
    1. /event_dates から今日の日付ページURLを取得
    2. 日付ページから競馬場リストを取得
    3. 各競馬場ページから全レースリンクを取得
    4. 各レースページからAI指数をスクレイピング

    Returns:
        dict: {"success": bool, "races_scraped": int, "errors": list}
    """
    table = get_dynamodb_table()
    scraped_at = datetime.now(JST)
    date_str = scraped_at.strftime("%Y%m%d")
    target_date = f"{scraped_at.month}/{scraped_at.day}"  # "1/31" 形式

    results = {
        "success": True,
        "races_scraped": 0,
        "errors": [],
    }

    # Step 1: 開催日一覧ページを取得
    logger.info(f"Fetching event dates from {EVENT_DATES_URL}")
    dates_soup = fetch_page(EVENT_DATES_URL)
    if not dates_soup:
        results["success"] = False
        results["errors"].append("Failed to fetch event dates page")
        return results

    # 今日の日付リンクを探す
    today_url = find_today_event_date_url(dates_soup, target_date)
    if not today_url:
        results["errors"].append(f"No event found for date {target_date}")
        return results

    logger.info(f"Found today's event page: {today_url}")

    # Step 2: 日付ページから競馬場リストを取得
    time.sleep(REQUEST_DELAY_SECONDS)
    date_page_url = BASE_URL + today_url
    date_soup = fetch_page(date_page_url)
    if not date_soup:
        results["success"] = False
        results["errors"].append(f"Failed to fetch date page: {today_url}")
        return results

    venues = parse_venue_list(date_soup)
    logger.info(f"Found {len(venues)} JRA venues")

    if not venues:
        results["errors"].append("No JRA venues found for today")
        return results

    # Step 3: 各競馬場ページからレースリストを取得
    all_races = []
    for venue_info in venues:
        venue_url = BASE_URL + venue_info["url"]
        venue = venue_info["venue"]

        logger.info(f"Fetching races for {venue}: {venue_url}")
        time.sleep(REQUEST_DELAY_SECONDS)

        venue_soup = fetch_page(venue_url)
        if not venue_soup:
            results["errors"].append(f"Failed to fetch venue page: {venue}")
            continue

        races = parse_race_list(venue_soup, venue)
        logger.info(f"Found {len(races)} races at {venue}")
        all_races.extend(races)

    if not all_races:
        results["errors"].append("No races found")
        return results

    logger.info(f"Total races to scrape: {len(all_races)}")

    # Step 4: 各レースのAI指数を取得
    for race_info in all_races:
        race_url = BASE_URL + race_info["url"]
        venue = race_info["venue"]
        race_number = race_info["race_number"]

        logger.info(f"Scraping {venue} {race_number}R: {race_url}")

        time.sleep(REQUEST_DELAY_SECONDS)

        race_soup = fetch_page(race_url)
        if not race_soup:
            results["errors"].append(f"Failed to fetch {venue} {race_number}R")
            continue

        predictions = parse_race_predictions(race_soup)
        if not predictions:
            results["errors"].append(f"No predictions found for {venue} {race_number}R")
            continue

        race_id = generate_race_id(date_str, venue, race_number)

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
