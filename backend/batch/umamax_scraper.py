"""うままっくす スクレイピング Lambda.

umamax.com から競馬AIうままっくすのUM指数を取得し、DynamoDBに保存する。

サイト構造:
- トップページに日付・競馬場別の予想記事リンクが掲載
- URL形式: /YYYY-MM-DD-{venue}-yosou-{range}/
  例: /2026-02-08-kyoto-yosou-7r-12r/
- 各記事ページにテーブルで予想データを掲載
- テーブルカラム: 印 | 番 | 馬名 | UM指数 | 差
- 各記事は前半(1R-6R)と後半(7R-12R)に分割
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
BASE_URL = "https://umamax.com"
SOURCE_NAME = "umamax"
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 1.0  # サーバー負荷軽減のための遅延

# タイムゾーン
JST = timezone(timedelta(hours=9))

# URLの競馬場名マッピング（URL slug → 日本語名）
VENUE_SLUG_MAP = {
    "sapporo": "札幌",
    "hakodate": "函館",
    "fukushima": "福島",
    "niigata": "新潟",
    "tokyo": "東京",
    "nakayama": "中山",
    "chukyo": "中京",
    "kyoto": "京都",
    "hanshin": "阪神",
    "kokura": "小倉",
}

# 印記号（テーブル内の印カラム）
MARK_CHARS = re.compile(r"[◎〇○▲△☆×]")


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


def find_prediction_article_urls(soup: BeautifulSoup, target_date_str: str) -> list[dict]:
    """トップページから対象日付の予想記事URLを探す.

    URL形式: /YYYY-MM-DD-{venue}-yosou-{range}/
    例:
      /2026-02-08-kyoto-yosou-7r-12r/ → 京都 7R-12R
      /2026-02-08-tokyo-yosou-1r-6r/ → 東京 1R-6R

    Args:
        soup: トップページのBeautifulSoup
        target_date_str: 対象日付 (例: "20260208")

    Returns:
        list of dict: [{"url": "https://...", "venue": "京都", "start_race": 7, "end_race": 12}, ...]
    """
    articles = []
    # 日付をURL形式に変換: "20260208" → "2026-02-08"
    year = target_date_str[:4]
    month = target_date_str[4:6]
    day = target_date_str[6:8]
    date_slug = f"{year}-{month}-{day}"

    # パターン: /2026-02-08-kyoto-yosou-7r-12r/
    url_pattern = re.compile(
        rf"https?://umamax\.com/{date_slug}-(\w+)-yosou-(\d+)r-(\d+)r/"
    )

    for link in soup.find_all("a", href=url_pattern):
        href = link.get("href", "")
        match = url_pattern.search(href)
        if not match:
            continue

        venue_slug = match.group(1)
        start_race = int(match.group(2))
        end_race = int(match.group(3))

        venue = VENUE_SLUG_MAP.get(venue_slug)
        if not venue:
            continue

        # 重複チェック
        if any(a["url"] == href for a in articles):
            continue

        articles.append({
            "url": href,
            "venue": venue,
            "start_race": start_race,
            "end_race": end_race,
        })

    return articles


def parse_race_predictions_page(soup: BeautifulSoup, venue: str, start_race: int) -> list[dict]:
    """予想記事ページから全レースのUM指数データを抽出.

    ページ構造:
    - h2/h3タグ: "京都07R ４上 １勝クラス・牝 ダ1800" のようなレース見出し
    - table: 印 | 番 | 馬名 | UM指数 | 差

    Args:
        soup: 記事ページのBeautifulSoup
        venue: 競馬場名 (例: "京都")
        start_race: 開始レース番号 (例: 7)

    Returns:
        list of dict: [{
            "venue": "京都",
            "race_number": 7,
            "predictions": [{"rank": 1, "score": 52.4, "horse_number": 5, "horse_name": "xxx"}, ...]
        }, ...]
    """
    races = []

    # レース見出しを探す（h2/h3タグ）
    content = soup.find("div", class_="entry-content") or soup.find("article") or soup

    # テーブルを全て取得
    tables = content.find_all("table")

    # レース見出しからレース番号を抽出
    headings = content.find_all(["h2", "h3"])
    race_headings = []
    for h in headings:
        text = h.get_text(strip=True)
        # "京都07R ４上 ..." のパターンからレース番号を抽出
        match = re.search(r"(\d+)R", text)
        if match:
            race_number = int(match.group(1))
            race_headings.append({"element": h, "race_number": race_number})

    # 見出しとテーブルを対応付ける
    if race_headings and tables:
        # 見出しの後にあるテーブルを対応付ける
        for i, heading_info in enumerate(race_headings):
            race_number = heading_info["race_number"]
            heading_elem = heading_info["element"]

            # この見出しの後にある最初のテーブルを探す
            table = _find_next_table(heading_elem)
            if not table:
                # テーブルの順番で対応（フォールバック）
                if i < len(tables):
                    table = tables[i]

            if table:
                predictions = _parse_umamax_table(table)
                if predictions:
                    races.append({
                        "venue": venue,
                        "race_number": race_number,
                        "predictions": predictions,
                    })
    elif tables:
        # 見出しがない場合、テーブルの順番でレース番号を推定
        for i, table in enumerate(tables):
            predictions = _parse_umamax_table(table)
            if predictions:
                race_number = start_race + i
                races.append({
                    "venue": venue,
                    "race_number": race_number,
                    "predictions": predictions,
                })

    return races


def _find_next_table(element) -> BeautifulSoup | None:
    """指定要素の後にある最初のtableを探す."""
    sibling = element.find_next_sibling()
    while sibling:
        if sibling.name == "table":
            return sibling
        # div等の中にtableがある場合
        table = sibling.find("table")
        if table:
            return table
        # 次の見出しに到達したら終了
        if sibling.name in ("h2", "h3"):
            break
        sibling = sibling.find_next_sibling()
    # find_next_siblingで見つからない場合、find_nextで探す
    table = element.find_next("table")
    return table


def _parse_umamax_table(table: BeautifulSoup) -> list[dict]:
    """うままっくすの予想テーブルからデータを抽出.

    カラム構造: 印 | 番 | 馬名 | UM指数 | 差

    Returns:
        list of dict: [{"rank": 1, "score": 52.4, "horse_number": 5, "horse_name": "xxx"}, ...]
    """
    predictions = []
    rows = table.find_all("tr")

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue

        cell_texts = [cell.get_text(strip=True) for cell in cells]

        # ヘッダー行をスキップ（"印", "番", "馬名" などを含む行）
        if "印" in cell_texts[0] or "番" in cell_texts[1] or "馬名" in cell_texts[2]:
            continue

        try:
            # 印（1列目）- 使用しないが存在確認
            # 馬番（2列目）
            horse_number = int(cell_texts[1])

            # 馬名（3列目）
            horse_name = cell_texts[2]

            # UM指数（4列目）
            score = float(cell_texts[3])

            if 1 <= horse_number <= 18 and horse_name:
                predictions.append({
                    "score": score,
                    "horse_number": horse_number,
                    "horse_name": horse_name,
                })
        except (ValueError, IndexError, TypeError):
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

    前日夜に翌日分のUM指数を取得する。
    umamax.com は前日にデータを配信するため、毎晩21:00 JST に翌日分を取り込む。

    フロー:
    1. トップページから翌日の予想記事URL一覧を取得
    2. 各記事ページからUM指数をスクレイピング
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

    articles = find_prediction_article_urls(top_soup, date_str)
    if not articles:
        # 開催がない日は正常終了扱い
        logger.info(f"No prediction articles found for {date_str}")
        results["races_scraped"] = 0
        return results

    logger.info(f"Found {len(articles)} prediction articles for {date_str}")

    # Step 2: 各記事ページからUM指数を取得
    for article_info in articles:
        article_url = article_info["url"]
        venue = article_info["venue"]
        start_race = article_info["start_race"]

        logger.info(f"Scraping {venue} {start_race}R~: {article_url}")
        time.sleep(REQUEST_DELAY_SECONDS)

        article_soup = fetch_page(article_url)
        if not article_soup:
            results["errors"].append(f"Failed to fetch {venue} article")
            continue

        races = parse_race_predictions_page(article_soup, venue, start_race)
        if not races:
            results["errors"].append(f"No races found for {venue} {start_race}R~")
            continue

        # Step 3: DynamoDBに保存
        for race_info in races:
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
    logger.info(f"Starting umamax scraper: event={event}")

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
