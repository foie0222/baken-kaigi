"""kichiuma.net スピード指数スクレイピング Lambda.

吉馬（kichiuma.net）から競馬のスピード指数を取得し、DynamoDBに保存する。
中央競馬の無料WEB競馬新聞で、出馬表とスピード指数を提供。

URL構造:
  レース一覧: php/search.php?date=YYYY%2FM%2FD&id=VV
  SPランク:   php/search.php?race_id=RRR&date=YYYY%2FM%2FD&no=N&id=VV&p=ls

HTML構造 (SPランクページ):
  テーブルの各行(tr)が1馬のデータ。
  直接子tdが9セル: [馬番, 前走Rnk, 過去Rnk, 馬名, 前走指数, 2走前, 3走前, 4走前, 5走前]
  前走指数をspeed_indexとして使用する。
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

from batch.ai_shisu_scraper import VENUE_CODE_MAP
from batch.dynamodb_utils import convert_floats

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 定数
SOURCE_NAME = "kichiuma-speed"
BASE_URL = "https://kichiuma.net"
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 1.0

# タイムゾーン
JST = timezone(timedelta(hours=9))

# kichiuma.net の競馬場IDマッピング
# サイト独自のID -> 競馬場名
KICHIUMA_VENUE_ID_MAP = {
    "71": "札幌",
    "72": "函館",
    "73": "福島",
    "74": "新潟",
    "75": "東京",
    "76": "中山",
    "77": "中京",
    "78": "京都",
    "79": "阪神",
    "80": "小倉",
}

# 競馬場名 -> kichiumaのID
VENUE_NAME_TO_KICHIUMA_ID = {v: k for k, v in KICHIUMA_VENUE_ID_MAP.items()}


def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("SPEED_INDICES_TABLE_NAME", "baken-kaigi-speed-indices")
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
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def find_venues_from_top_page(soup: BeautifulSoup) -> list[dict]:
    """トップページから本日の開催競馬場情報を取得.

    トップページの地図下のリンクから、開催競馬場を特定する。
    リンク: php/search.php?date=YYYY%2FM%2FD&id=VV

    Returns:
        list of dict: [{"venue": "東京", "venue_id": "75", "date_param": "2026%2F2%2F8"}, ...]
    """
    venues = []
    seen_ids = set()

    for link in soup.find_all("a", href=re.compile(r"search\.php\?date=")):
        href = link.get("href", "")

        # dateとidパラメータを抽出
        date_match = re.search(r"date=([^&]+)", href)
        id_match = re.search(r"id=(\d+)", href)

        if not date_match or not id_match:
            continue

        venue_id = id_match.group(1)
        date_param = date_match.group(1)

        # 既知の競馬場IDのみ対象
        venue_name = KICHIUMA_VENUE_ID_MAP.get(venue_id)
        if not venue_name:
            continue

        if venue_id not in seen_ids:
            seen_ids.add(venue_id)
            venues.append({
                "venue": venue_name,
                "venue_id": venue_id,
                "date_param": date_param,
            })

    return venues


def parse_race_list(soup: BeautifulSoup, venue_id: str, date_param: str) -> list[dict]:
    """競馬場ページからレース一覧を抽出.

    Args:
        soup: 競馬場ページのBeautifulSoup
        venue_id: kichiuma venue ID (例: "75")
        date_param: URLの日付パラメータ (例: "2026%2F2%2F8")

    Returns:
        list of dict: [{"race_number": 1, "race_id_param": "202602080175", ...}, ...]
    """
    races = []

    # SPランク(p=ls)のリンクを探す
    for link in soup.find_all("a", href=re.compile(r"p=ls")):
        href = link.get("href", "")

        # race_id, no(レース番号)を抽出
        race_id_match = re.search(r"race_id=(\d+)", href)
        no_match = re.search(r"no=(\d+)", href)

        if not race_id_match or not no_match:
            continue

        race_number = int(no_match.group(1))
        race_id_param = race_id_match.group(1)

        races.append({
            "race_number": race_number,
            "race_id_param": race_id_param,
            "href": href,
        })

    return races


def parse_speed_index_page(soup: BeautifulSoup) -> list[dict]:
    """SPランクページからスピード指数データを抽出.

    テーブル構造:
    - ヘッダー行(th): [馬, 前走Rnk, 過去Rnk, 競走馬名, 前走, 過去走(2～5走前)]
    - データ行(td, 9セル): [馬番, 前走Rnk, 過去Rnk, 馬名, 前走指数, 2走前, 3走前, 4走前, 5走前]

    Returns:
        list of dict: [{"horse_number": 1, "horse_name": "xxx", "speed_index": 92.0}, ...]
    """
    results = []

    # ヘッダーに「馬」「前走Rnk」を含むテーブルを探す
    tables = soup.find_all("table")

    target_table = None
    for table in tables:
        ths = table.find_all("th")
        th_texts = [th.get_text(strip=True) for th in ths]
        if "馬" in th_texts and "前走Rnk" in th_texts:
            # 6つのthヘッダーを持つテーブル（広告等でないもの）
            if len(th_texts) == 6:
                target_table = table
                break

    if not target_table:
        return []

    # ネストされたテーブル構造のため、全trを取得して9セルの行をフィルタ
    trs = target_table.find_all("tr")

    for tr in trs:
        tds = tr.find_all("td", recursive=False)
        if len(tds) != 9:
            continue

        cell_texts = [td.get_text(strip=True) for td in tds]

        try:
            horse_number = int(cell_texts[0])
            horse_name = cell_texts[3]
            speed_index = float(cell_texts[4])  # 前走指数

            if 1 <= horse_number <= 18 and speed_index > 0 and horse_name:
                results.append({
                    "horse_number": horse_number,
                    "horse_name": horse_name,
                    "speed_index": speed_index,
                })
        except (ValueError, IndexError):
            continue

    # speed_index降順でrank付与
    results.sort(key=lambda x: x["speed_index"], reverse=True)
    for rank, entry in enumerate(results, 1):
        entry["rank"] = rank

    return results


def generate_race_id(date_str: str, venue: str, race_number: int) -> str:
    """JRA-VANスタイルのrace_idを生成."""
    venue_code = VENUE_CODE_MAP.get(venue, "00")
    return f"{date_str}_{venue_code}_{race_number:02d}"


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

    フロー:
    1. トップページから翌日の開催競馬場を特定
    2. 各競馬場のレース一覧ページからSPランクリンクを取得
    3. 各レースのSPランクページからスピード指数を抽出
    """
    table = get_dynamodb_table()
    scraped_at = datetime.now(JST)
    tomorrow = scraped_at + timedelta(days=1)
    date_str = tomorrow.strftime("%Y%m%d")
    date_param = f"{tomorrow.year}%2F{tomorrow.month}%2F{tomorrow.day}"

    results = {
        "success": True,
        "races_scraped": 0,
        "errors": [],
    }

    # Step 1: 翌日の開催競馬場を特定
    # 直接各競馬場のレース一覧ページにアクセスして存在確認する
    venues = []
    for venue_id, venue_name in KICHIUMA_VENUE_ID_MAP.items():
        venue_url = f"{BASE_URL}/php/search.php?date={date_param}&id={venue_id}"

        logger.info(f"Checking venue: {venue_name} ({venue_url})")
        time.sleep(REQUEST_DELAY_SECONDS)

        venue_soup = fetch_page(venue_url)
        if not venue_soup:
            continue

        # タイトルに「エラー」が含まれない場合は開催あり
        title = venue_soup.find("title")
        if title and "エラー" not in title.get_text():
            venues.append({
                "venue": venue_name,
                "venue_id": venue_id,
                "date_param": date_param,
                "soup": venue_soup,
            })

    if not venues:
        logger.info(f"No venues found for {date_str}")
        results["races_scraped"] = 0
        return results

    logger.info(f"Found {len(venues)} venues")

    # Step 2-3: 各競馬場のレースをスクレイピング
    for venue_info in venues:
        venue = venue_info["venue"]
        venue_id = venue_info["venue_id"]
        venue_soup = venue_info["soup"]

        races = parse_race_list(venue_soup, venue_id, date_param)
        logger.info(f"Found {len(races)} races at {venue}")

        for race in races:
            race_number = race["race_number"]
            race_href = race["href"]

            # SPランクページを取得
            sp_url = f"{BASE_URL}/php/{race_href}" if not race_href.startswith("http") else race_href
            # 相対パスの../を処理
            if "../" in sp_url:
                sp_url = f"{BASE_URL}/{race_href.lstrip('../')}"

            logger.info(f"Scraping {venue} {race_number}R SP rank: {sp_url}")
            time.sleep(REQUEST_DELAY_SECONDS)

            sp_soup = fetch_page(sp_url)
            if not sp_soup:
                results["errors"].append(f"Failed to fetch {venue} {race_number}R SP")
                continue

            indices = parse_speed_index_page(sp_soup)
            if not indices:
                results["errors"].append(f"No indices found for {venue} {race_number}R")
                continue

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
    logger.info(f"Starting kichiuma scraper: event={event}")

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
