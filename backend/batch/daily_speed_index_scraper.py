"""daily.co.jp スピード指数スクレイピング Lambda.

デイリースポーツ（daily.co.jp）からスピード指数データを取得し、DynamoDBに保存する。
走破タイムから算出した能力指数を提供。毎週水曜17時までに翌週分を更新。

URL構造:
  一覧ページ: https://www.daily.co.jp/horse/speed/
  日付ページ: https://www.daily.co.jp/horse/speed/data/NNNNNNNNNN.shtml

HTML構造 (日付ページ):
  1つのテーブルに全レースが含まれる。
  ヘッダー行(0): [日付, 場所, R, 条件, 距離, 芝ダ, 頭数, 1番, 指数, 2番, 指数, ... 18番, 指数, ...]
  データ行: [YYYYMMDD, 場所, R番号, 条件, 距離, 芝ダ, 頭数, 丸数字馬番, 指数, ...]
  馬番は丸数字(①～⑱)、指数はint型。
"""

import logging
import os
import re
import time
import unicodedata
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
SOURCE_NAME = "daily-speed"
BASE_URL = "https://www.daily.co.jp/horse/speed"
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 2.0  # 大手メディアサイトなので長めに設定

# タイムゾーン
JST = timezone(timedelta(hours=9))

# 丸数字→整数のマッピング
CIRCLED_NUMBER_MAP = {
    "\u2460": 1, "\u2461": 2, "\u2462": 3, "\u2463": 4, "\u2464": 5,
    "\u2465": 6, "\u2466": 7, "\u2467": 8, "\u2468": 9, "\u2469": 10,
    "\u246a": 11, "\u246b": 12, "\u246c": 13, "\u246d": 14, "\u246e": 15,
    "\u246f": 16, "\u2470": 17, "\u2471": 18,
}


def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("SPEED_INDICES_TABLE_NAME", "baken-kaigi-speed-indices")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def fetch_page(url: str) -> BeautifulSoup | None:
    """ページを取得してBeautifulSoupオブジェクトを返す."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def normalize_fullwidth(text: str) -> str:
    """全角数字を半角に変換."""
    return unicodedata.normalize("NFKC", text)


def parse_circled_number(text: str) -> int:
    """丸数字を整数に変換.

    Args:
        text: 丸数字を含むテキスト (例: "⑬")

    Returns:
        int: 馬番 (1-18)。変換できない場合は0。
    """
    text = text.strip()
    for char in text:
        if char in CIRCLED_NUMBER_MAP:
            return CIRCLED_NUMBER_MAP[char]
    return 0


def find_date_page_url(soup: BeautifulSoup, target_month: int, target_day: int) -> str | None:
    """一覧ページから対象日付のリンクを探す.

    リンクテキストは「２月８日（土曜日）」のような全角混じりの形式。

    Args:
        soup: 一覧ページのBeautifulSoup
        target_month: 対象月 (例: 2)
        target_day: 対象日 (例: 8)

    Returns:
        str | None: 日付ページURL (例: "/horse/speed/data/0013109970.shtml")
    """
    for link in soup.find_all("a", href=re.compile(r"/horse/speed/data/\d+\.shtml")):
        text = link.get_text(strip=True)
        # 全角→半角正規化
        normalized = normalize_fullwidth(text)

        # "2月8日" や "2月08日" のパターンにマッチ
        match = re.search(r"(\d+)月\s*(\d+)日", normalized)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            if month == target_month and day == target_day:
                return link.get("href", "")

    return None


def parse_race_data(soup: BeautifulSoup, target_date_str: str) -> list[dict]:
    """日付ページから全レースのスピード指数データを抽出.

    Args:
        soup: 日付ページのBeautifulSoup
        target_date_str: 対象日付 (例: "20260208")

    Returns:
        list of dict: [{
            "venue": "東京",
            "race_number": 11,
            "indices": [{"horse_number": 13, "speed_index": 339.0, ...}, ...]
        }, ...]
    """
    tables = soup.find_all("table")
    if not tables:
        return []

    # データテーブルを探す（最も多くのtdを持つテーブル）
    main_table = max(tables, key=lambda t: len(t.find_all("td")))

    trs = main_table.find_all("tr")
    if len(trs) < 2:
        return []

    races = []

    for tr in trs[1:]:  # ヘッダー行をスキップ
        tds = tr.find_all("td")
        if len(tds) < 43:
            continue

        cell_texts = [td.get_text(strip=True) for td in tds]

        # 基本情報を抽出
        date_val = cell_texts[0]
        venue_name = cell_texts[1]
        race_num_str = cell_texts[2]

        # 対象日付のデータのみ処理
        if date_val != target_date_str:
            continue

        # JRA中央競馬場のみ対象
        if venue_name not in VENUE_CODE_MAP:
            continue

        try:
            race_number = int(race_num_str)
        except ValueError:
            continue

        # スピード指数を抽出（7番目以降、18ペア=36セル）
        indices = []
        for i in range(18):
            horse_idx = 7 + i * 2
            index_idx = 8 + i * 2

            if horse_idx >= len(cell_texts) or index_idx >= len(cell_texts):
                break

            horse_text = cell_texts[horse_idx]
            index_text = cell_texts[index_idx]

            if not horse_text or not index_text:
                continue

            horse_number = parse_circled_number(horse_text)
            if horse_number == 0:
                continue

            try:
                speed_index = float(index_text)
            except ValueError:
                continue

            if speed_index > 0:
                indices.append({
                    "horse_number": horse_number,
                    "speed_index": speed_index,
                    "horse_name": "",  # daily.co.jpは馬名を提供しない
                })

        if indices:
            # speed_index降順でrank付与
            indices.sort(key=lambda x: x["speed_index"], reverse=True)
            for rank, entry in enumerate(indices, 1):
                entry["rank"] = rank

            races.append({
                "venue": venue_name,
                "race_number": race_number,
                "indices": indices,
            })

    return races


def generate_race_id(date_str: str, venue: str, race_number: int) -> str:
    """JRA-VANスタイルのrace_idを生成."""
    venue_code = VENUE_CODE_MAP.get(venue, "00")
    return f"{date_str}{venue_code}{race_number:02d}"


def save_indices(
    table,
    race_id: str,
    venue: str,
    race_number: int,
    indices: list[dict],
    scraped_at: datetime,
) -> None:
    """スピード指数データをDynamoDBに保存."""
    ttl = int((scraped_at + timedelta(days=TTL_DAYS)).timestamp())

    item = {
        "race_id": race_id,
        "source": SOURCE_NAME,
        "venue": venue,
        "race_number": race_number,
        "indices": convert_floats(indices),
        "scraped_at": scraped_at.isoformat(),
        "ttl": ttl,
    }

    table.put_item(Item=item)
    logger.info(f"Saved indices for {race_id}: {len(indices)} horses")


def scrape_races() -> dict[str, Any]:
    """メインのスクレイピング処理.

    翌日分のスピード指数を取得する。
    デイリーは水曜に週末分をまとめて公開するため、木曜以降に取得可能。

    フロー:
    1. 一覧ページから対象日付のリンクを取得
    2. 日付ページから全レースのスピード指数を抽出
    3. DynamoDBに保存
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

    # Step 1: 一覧ページから日付リンクを探す
    logger.info(f"Fetching index page from {BASE_URL}/")
    index_soup = fetch_page(f"{BASE_URL}/")
    if not index_soup:
        results["success"] = False
        results["errors"].append("Failed to fetch index page")
        return results

    date_url = find_date_page_url(index_soup, tomorrow.month, tomorrow.day)
    if not date_url:
        # データがまだ公開されていない可能性がある
        logger.info(f"No data page found for {tomorrow.month}/{tomorrow.day}")
        results["races_scraped"] = 0
        return results

    # 完全URLを構築
    if date_url.startswith("/"):
        full_url = f"https://www.daily.co.jp{date_url}"
    else:
        full_url = date_url

    logger.info(f"Found date page: {full_url}")

    # Step 2: 日付ページからデータを取得
    time.sleep(REQUEST_DELAY_SECONDS)
    date_soup = fetch_page(full_url)
    if not date_soup:
        results["success"] = False
        results["errors"].append(f"Failed to fetch date page: {date_url}")
        return results

    races = parse_race_data(date_soup, date_str)
    logger.info(f"Found {len(races)} races")

    if not races:
        results["errors"].append("No races found in date page")
        return results

    # Step 3: DynamoDBに保存
    for race in races:
        venue = race["venue"]
        race_number = race["race_number"]
        indices = race["indices"]

        race_id = generate_race_id(date_str, venue, race_number)

        try:
            save_indices(
                table=table,
                race_id=race_id,
                venue=venue,
                race_number=race_number,
                indices=indices,
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
    """Lambda ハンドラー."""
    logger.info(f"Starting daily speed index scraper: event={event}")

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
