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
from batch.dynamodb_utils import convert_floats

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 定数
BASE_URL = "https://muryou-keiba-ai.jp"
SOURCE_NAME = "muryou-keiba-ai"
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 1.0  # サーバー負荷軽減のための遅延
MAX_ARCHIVE_PAGES = 5  # 月後半はレースが2ページ目以降に押し出されるため

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

    URLの日付は記事公開日であり、レース日とは異なる。
    レース日はリンクテキスト内の「M月D日」から判定する。

    Args:
        soup: アーカイブページのBeautifulSoup
        target_date_str: 対象日付 (例: "20260208")

    Returns:
        list of dict: [{"url": "https://...", "venue": "京都", "race_number": 1, "date_str": "20260208"}, ...]
    """
    races = []

    # target_date_str から月・日を数値で取得
    target_month = int(target_date_str[4:6])
    target_day = int(target_date_str[6:8])

    # URL形式: /predict/YYYY/MM/DD/ID/
    url_pattern = re.compile(
        r"https?://muryou-keiba-ai\.jp/predict/\d{4}/\d{2}/\d{2}/\d+/"
    )

    # リンクテキストからレース日を抽出する正規表現
    date_pattern = re.compile(r"(\d{1,2})月(\d{1,2})日")

    for link in soup.find_all("a", href=url_pattern):
        href = link.get("href", "")

        # リンクテキストからレース情報を抽出
        text = link.get_text(strip=True)

        # レース日をリンクテキストからパースして厳密一致判定
        date_match = date_pattern.search(text)
        if not date_match:
            continue
        text_month = int(date_match.group(1))
        text_day = int(date_match.group(2))
        if text_month != target_month or text_day != target_day:
            continue

        info = extract_race_info(text)
        if not info:
            continue

        races.append({
            "url": href,
            "venue": info["venue"],
            "race_number": info["race_number"],
            "date_str": target_date_str,
        })

    return races


def parse_race_predictions(soup: BeautifulSoup) -> list[dict]:
    """レースページからAI予想データを抽出.

    実際のHTML構造:
    <table class="race_table baken_race_table">
      <tr>
        <td><p class="umaban_wrap waku_2">2</p></td>
        <td><p class="bamei_wrap"><a class="bamei"><strong>馬名</strong></a></p></td>
        <td><p class="predict_wrap predict_1"><span class="mark">◎</span><span class="predict">65.7</span></p></td>
      </tr>

    Returns:
        list of dict: [{"rank": 1, "score": 65.7, "horse_number": 2, "horse_name": "xxx"}, ...]
    """
    predictions = []

    # baken_race_table を優先、なければ race_table にフォールバック
    table = soup.find("table", class_="baken_race_table")
    if not table:
        table = soup.find("table", class_="race_table")
    if not table:
        return []

    rows = table.find_all("tr")

    for row in rows:
        # クラスは<p>要素にあるため、タグを限定せず検索
        umaban_el = row.find(class_=re.compile(r"umaban_wrap"))
        bamei_el = row.find(class_=re.compile(r"bamei_wrap"))
        predict_el = row.find(class_=re.compile(r"predict_wrap"))

        if not (umaban_el and bamei_el and predict_el):
            continue

        try:
            horse_number = int(umaban_el.get_text(strip=True))
        except (ValueError, TypeError):
            continue

        # 馬名: <a class="bamei">内のテキストを優先
        bamei_link = bamei_el.find("a", class_="bamei")
        if bamei_link:
            horse_name = bamei_link.get_text(strip=True)
        else:
            horse_name = bamei_el.get_text(strip=True)
        if not horse_name:
            continue

        # スコア抽出: <span class="predict">を優先、なければmarkテキストからパース
        predict_span = predict_el.find("span", class_="predict")
        if predict_span:
            score_text = predict_span.get_text(strip=True)
        else:
            mark_el = predict_el.find(class_="mark")
            if not mark_el:
                continue
            score_text = mark_el.get_text(strip=True)
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
        str: race_id (例: "202602080811")
    """
    venue_code = VENUE_CODE_MAP.get(venue, "00")
    return f"{date_str}{venue_code}{race_number:02d}"


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


def scrape_races(offset_days: int = 1) -> dict[str, Any]:
    """メインのスクレイピング処理.

    muryou-keiba-ai.jp のアーカイブページからレース一覧を取得し、
    各レースページからAI予想をスクレイピングする。

    Args:
        offset_days: 何日後のレースを取得するか。
            0 = 当日（レース当日朝の最終更新版取得用）
            1 = 翌日（前日夜の早期取得用、デフォルト）

    フロー:
    1. /predict/?y=YYYY&month=MM からレース一覧を取得
    2. 各レースページからAI予想をスクレイピング
    3. DynamoDBに保存

    Returns:
        dict: {"success": bool, "races_scraped": int, "errors": list}
    """
    table = get_dynamodb_table()
    scraped_at = datetime.now(JST)
    target_date = scraped_at + timedelta(days=offset_days)
    date_str = target_date.strftime("%Y%m%d")

    results = {
        "success": True,
        "races_scraped": 0,
        "errors": [],
    }

    # Step 1: アーカイブページからレース一覧を取得（ページネーション対応）
    races: list[dict] = []
    for page in range(1, MAX_ARCHIVE_PAGES + 1):
        if page == 1:
            archive_url = f"{BASE_URL}/predict/?y={target_date.year}&month={target_date.month:02d}"
        else:
            archive_url = f"{BASE_URL}/predict/page/{page}/?y={target_date.year}&month={target_date.month:02d}"
        logger.info(f"Fetching archive page {page}: {archive_url}")
        archive_soup = fetch_page(archive_url)
        if not archive_soup:
            results["success"] = False
            results["errors"].append(f"Failed to fetch archive page {page}")
            return results
        page_races = parse_race_list_page(archive_soup, date_str)
        races.extend(page_races)
        if page_races:
            logger.info(f"Found {len(page_races)} races on page {page}")
            break  # 対象日のレースが見つかったらそれ以上ページを辿らない
        time.sleep(REQUEST_DELAY_SECONDS)

    if not races:
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
        offset_days = int(event.get("offset_days", 1))
    except (TypeError, ValueError):
        offset_days = 1
    if offset_days not in (0, 1):
        offset_days = 1

    try:
        results = scrape_races(offset_days=offset_days)
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
