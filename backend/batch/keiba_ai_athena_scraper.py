"""競馬AI ATHENA スクレイピング Lambda.

keiba-ai.jp から競馬AI ATHENAの予想を取得し、DynamoDBに保存する。

サイト構造:
- トップページに日付別の記事リンクが掲載
- 各記事ページに複数競馬場のレース予想がまとまっている
- h2タグで競馬場区切り（京都、東京など）
- su-box-title でレース番号（01R～12R）
- table#uma-table2 に予想データ（馬番、馬名、AI指数、予想着順）
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
BASE_URL = "https://keiba-ai.jp"
SOURCE_NAME = "keiba-ai-athena"
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


def find_prediction_article_url(soup: BeautifulSoup, target_date_str: str) -> str | None:
    """トップページから対象日付のAI予想記事URLを探す.

    記事タイトル例: "2026年02月08日(日)のレースAI予想【きさらぎ賞、東京新聞杯】など"
    結果記事とは区別する（"結果" を含まない方を選ぶ）

    Args:
        soup: トップページのBeautifulSoup
        target_date_str: 対象日付 (例: "20260208")

    Returns:
        str | None: 記事URL (例: "https://keiba-ai.jp/archives/2969") または None
    """
    # 日付をフォーマット: "2026年02月08日"
    year = target_date_str[:4]
    month = target_date_str[4:6]
    day = target_date_str[6:8]
    formatted_date = f"{year}年{month}月{day}日"

    for link in soup.find_all("a", href=re.compile(r"https://keiba-ai\.jp/archives/\d+")):
        text = link.get_text(strip=True)
        # 対象日付を含み、「結果」を含まない記事を探す
        if formatted_date in text and "結果" not in text and "AI予想" in text:
            return link.get("href", "")

    return None


def parse_race_predictions_page(soup: BeautifulSoup) -> list[dict]:
    """予想記事ページから全レースのAI予想データを抽出.

    ページ構造:
    - h2タグ: 競馬場名（京都、東京、小倉など）
    - su-box-title: "01R\\n3歳未勝利" のようなレース見出し
    - table#uma-table2: 予想データテーブル

    テーブルのカラム:
    | 番 | 馬名(父) | 性齢斤量 | 騎手 | オッズ | 人気 | 予想勝率(AI指数) | 予想着順 | 確定着順 |

    Returns:
        list of dict: [{
            "venue": "京都",
            "race_number": 1,
            "predictions": [{"rank": 1, "score": 755, "horse_number": 14, "horse_name": "xxx"}, ...]
        }, ...]
    """
    races = []
    current_venue = None

    # ページ内の要素を順番に処理
    # h2 → 競馬場名、su-box → レース情報、table → 予想データ
    content = soup.find("div", class_="entry-body")
    if not content:
        # 別のコンテンツラッパーを試す
        content = soup.find("article") or soup

    # h2タグで競馬場区切り。サイトのHTMLではh2がネスト構造になっている場合がある。
    # h2の直接テキスト子要素が競馬場名（"京都", "東京"等）。
    # find_allはドキュメント順で返すため、h2 → div/table の順でイテレートすれば
    # 正しく会場が切り替わる。h2.get_text()は子孫全テキストを返すため使えない。
    elements = content.find_all(["h2", "div", "table"])

    current_race_number = None
    for elem in elements:
        # h2タグ: 競馬場名（直接テキスト子要素から取得）
        if elem.name == "h2":
            for child in elem.children:
                if isinstance(child, str):
                    t = child.strip()
                    if t and t in VENUE_CODE_MAP:
                        current_venue = t
                        logger.info(f"Found venue: {current_venue}")
                        break

        # su-box-title: レース番号
        elif elem.name == "div" and elem.get("class") and any(
            "su-box-title" in c for c in elem.get("class", [])
        ):
            text = elem.get_text(strip=True)
            match = re.match(r"(\d+)R", text)
            if match:
                current_race_number = int(match.group(1))

        # table: 予想データ
        elif elem.name == "table" and current_venue and current_race_number:
            predictions = _parse_athena_table(elem)
            if predictions:
                races.append({
                    "venue": current_venue,
                    "race_number": current_race_number,
                    "predictions": predictions,
                })
                current_race_number = None  # 次のレースへ

    return races


def _parse_athena_table(table: BeautifulSoup) -> list[dict]:
    """ATHENAの予想テーブルからデータを抽出.

    カラム構造: 番 | 馬名(父) | 性齢斤量 | 騎手 | オッズ | 人気 | 予想勝率(AI指数) | 予想着順 | 確定着順
    AI指数は "17.113 %(755)" のような形式で、括弧内の数値を使用する。

    Returns:
        list of dict: [{"rank": 1, "score": 755, "horse_number": 14, "horse_name": "xxx"}, ...]
    """
    predictions = []
    rows = table.find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        try:
            # 馬番（1列目）
            horse_number = int(cells[0].get_text(strip=True))

            # 馬名（2列目、父名はspan等で分離されている場合がある）
            # "プレデンシアルヴァンスレーヴ" のようなテキスト
            horse_name_cell = cells[1]
            # 最初のテキストノードが馬名、spanの中が父名
            horse_name = ""
            for child in horse_name_cell.children:
                if isinstance(child, str):
                    name = child.strip()
                    if name:
                        horse_name = name
                        break
                elif child.name and child.name != "span" and child.name != "br":
                    name = child.get_text(strip=True)
                    if name:
                        horse_name = name
                        break
            if not horse_name:
                horse_name = horse_name_cell.get_text(strip=True).split("\n")[0].strip()

            # AI指数（7列目: "17.113 %(755)"）
            score_text = cells[6].get_text(strip=True)
            # 括弧内の数値を抽出
            score_match = re.search(r"\((\d+)\)", score_text)
            if not score_match:
                continue
            score = int(score_match.group(1))

            # 予想着順（8列目）
            rank_text = cells[7].get_text(strip=True)
            try:
                rank = int(rank_text)
            except (ValueError, TypeError):
                rank = 0

            if 1 <= horse_number <= 18 and score > 0 and horse_name:
                predictions.append({
                    "rank": rank if rank > 0 else len(predictions) + 1,
                    "score": score,
                    "horse_number": horse_number,
                    "horse_name": horse_name,
                })
        except (ValueError, IndexError, TypeError):
            continue

    # スコア降順でソートしてランク再設定
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
        "predictions": predictions,
        "scraped_at": scraped_at.isoformat(),
        "ttl": ttl,
    }

    table.put_item(Item=item)
    logger.info(f"Saved predictions for {race_id}: {len(predictions)} horses")


def scrape_races() -> dict[str, Any]:
    """メインのスクレイピング処理.

    前日夜に翌日分のAI予想を取得する。
    keiba-ai.jp は前日18:00頃にデータを配信するため、毎晩21:00 JST に翌日分を取り込む。

    フロー:
    1. トップページから翌日の予想記事URLを取得
    2. 記事ページから全レースのAI予想をスクレイピング
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

    # Step 1: トップページから予想記事URLを取得
    logger.info(f"Fetching top page: {BASE_URL}")
    top_soup = fetch_page(BASE_URL)
    if not top_soup:
        results["success"] = False
        results["errors"].append("Failed to fetch top page")
        return results

    article_url = find_prediction_article_url(top_soup, date_str)
    if not article_url:
        # 開催がない日は正常終了扱い
        logger.info(f"No prediction article found for {date_str}")
        results["races_scraped"] = 0
        return results

    logger.info(f"Found prediction article: {article_url}")

    # Step 2: 記事ページから全レースの予想を取得
    time.sleep(REQUEST_DELAY_SECONDS)
    article_soup = fetch_page(article_url)
    if not article_soup:
        results["success"] = False
        results["errors"].append(f"Failed to fetch article: {article_url}")
        return results

    races = parse_race_predictions_page(article_soup)
    if not races:
        results["errors"].append("No races found in article")
        return results

    logger.info(f"Found {len(races)} races in article")

    # Step 3: DynamoDBに保存
    for race_info in races:
        venue = race_info["venue"]
        race_number = race_info["race_number"]
        predictions = race_info["predictions"]

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
    logger.info(f"Starting keiba-ai ATHENA scraper: event={event}")

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
