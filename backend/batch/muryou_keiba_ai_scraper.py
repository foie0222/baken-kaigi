"""無料競馬AI スクレイピング Lambda.

muryou-keiba-ai.jp から競馬のAI予想を取得し、DynamoDBに保存する。
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

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 定数
BASE_URL = "https://muryou-keiba-ai.jp"
SOURCE_NAME = "muryou-keiba-ai"
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 1.0  # サーバー負荷軽減のための遅延

# タイムゾーン
JST = timezone(timedelta(hours=9))

# AI予想の印記号（スコアから除去するため）
MARK_CHARS = re.compile(r"[◎○▲△☆]")


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


def extract_race_info(text: str) -> dict | None:
    """リンクテキストから競馬場名とレース番号を抽出.

    Args:
        text: リンクテキスト (例: "京都 2月8日 1R 09:55 3歳未勝利 ダート 1200m 16頭")

    Returns:
        dict | None: {"venue": "京都", "race_number": 1} または None
    """
    # レース番号を抽出
    race_match = re.search(r"(\d+)R", text)
    if not race_match:
        return None

    race_number = int(race_match.group(1))

    # 競馬場名を抽出（VENUE_CODE_MAPに含まれるもののみ）
    for venue in VENUE_CODE_MAP:
        if venue in text:
            return {"venue": venue, "race_number": race_number}

    return None


def parse_race_list_page(soup: BeautifulSoup, target_date_str: str) -> list[dict]:
    """アーカイブページからレース一覧を抽出.

    Args:
        soup: アーカイブページのBeautifulSoup
        target_date_str: 対象日付 (例: "20260208")

    Returns:
        list of dict: [{"url": "https://...", "venue": "京都", "race_number": 1, "date_str": "20260208"}, ...]
    """
    races = []

    # URL形式: /predict/YYYY/MM/DD/ID/
    url_pattern = re.compile(
        r"https?://muryou-keiba-ai\.jp/predict/(\d{4})/(\d{2})/(\d{2})/\d+/"
    )

    for link in soup.find_all("a", href=url_pattern):
        href = link.get("href", "")
        match = url_pattern.search(href)
        if not match:
            continue

        # URLから日付を抽出
        year, month, day = match.group(1), match.group(2), match.group(3)
        date_str = f"{year}{month}{day}"

        # 対象日付以外はスキップ
        if date_str != target_date_str:
            continue

        # リンクテキストからレース情報を抽出
        text = link.get_text(strip=True)
        info = extract_race_info(text)
        if not info:
            continue

        races.append({
            "url": href,
            "venue": info["venue"],
            "race_number": info["race_number"],
            "date_str": date_str,
        })

    return races


def parse_race_predictions(soup: BeautifulSoup) -> list[dict]:
    """レースページからAI予想データを抽出.

    テーブル構造:
    <table class="race_table">
      <tr>
        <td class="umaban_wrap">馬番</td>
        <td class="bamei_wrap">馬名</td>
        <td class="predict_wrap"><div class="mark">◎65.7</div></td>
      </tr>

    Returns:
        list of dict: [{"rank": 1, "score": 65.7, "horse_number": 2, "horse_name": "xxx"}, ...]
    """
    predictions = []

    # race_table クラスのテーブルを探す
    table = soup.find("table", class_="race_table")
    if not table:
        return []

    rows = table.find_all("tr")

    for row in rows:
        # 馬番セルを探す
        umaban_cell = row.find("td", class_=re.compile(r"umaban_wrap"))
        bamei_cell = row.find("td", class_=re.compile(r"bamei_wrap"))
        predict_cell = row.find("td", class_=re.compile(r"predict_wrap"))

        if not (umaban_cell and bamei_cell and predict_cell):
            continue

        try:
            horse_number = int(umaban_cell.get_text(strip=True))
        except (ValueError, TypeError):
            continue

        horse_name = bamei_cell.get_text(strip=True)
        if not horse_name:
            continue

        # スコアを抽出（印記号を除去）
        mark_div = predict_cell.find("div", class_="mark")
        if not mark_div:
            continue

        score_text = mark_div.get_text(strip=True)
        # 印記号を除去してスコアを取得
        score_text = MARK_CHARS.sub("", score_text).strip()

        try:
            score = float(score_text)
        except (ValueError, TypeError):
            continue

        predictions.append({
            "score": score,
            "horse_number": horse_number,
            "horse_name": horse_name,
        })

    # スコア降順でソートしてランク付け
    predictions.sort(key=lambda x: x["score"], reverse=True)
    for i, pred in enumerate(predictions):
        pred["rank"] = i + 1

    return predictions


def generate_race_id(date_str: str, venue: str, race_number: int) -> str:
    """JRA-VANスタイルのrace_idを生成.

    Args:
        date_str: 日付文字列 (例: "20260208")
        venue: 競馬場名 (例: "京都")
        race_number: レース番号 (例: 11)

    Returns:
        str: race_id (例: "20260208_08_11")
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

    前日夜に翌日分のAI予想を取得する。
    muryou-keiba-ai.jp のアーカイブページから翌日のレース一覧を取得し、
    各レースページからAI予想をスクレイピングする。

    フロー:
    1. /predict/?y=YYYY&month=MM から翌日のレース一覧を取得
    2. 各レースページからAI予想をスクレイピング
    3. DynamoDBに保存

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

    # Step 1: アーカイブページからレース一覧を取得
    archive_url = f"{BASE_URL}/predict/?y={tomorrow.year}&month={tomorrow.month:02d}"
    logger.info(f"Fetching archive page: {archive_url}")
    archive_soup = fetch_page(archive_url)
    if not archive_soup:
        results["success"] = False
        results["errors"].append("Failed to fetch archive page")
        return results

    races = parse_race_list_page(archive_soup, date_str)
    if not races:
        # 開催がない日は正常終了扱い
        logger.info(f"No JRA races found for {date_str}")
        results["races_scraped"] = 0
        return results

    logger.info(f"Found {len(races)} JRA races for {date_str}")

    # Step 2: 各レースページからAI予想を取得
    for race_info in races:
        race_url = race_info["url"]
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
    logger.info(f"Starting muryou-keiba-ai scraper: event={event}")

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
