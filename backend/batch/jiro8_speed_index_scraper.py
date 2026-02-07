"""jiro8.sakura.ne.jp スピード指数スクレイピング Lambda.

jiro8.sakura.ne.jp から競馬のスピード指数を取得し、DynamoDBに保存する。
西田式スピード指数ベースの無料データを提供する老舗サイト。

URL構造:
  index.php?code=YYVVRRDDNN
    YY = 年(2桁), VV = 競馬場コード(01-10), RR = 回, DD = 日, NN = レース番号

HTML構造:
  馬柱形式のテーブル。行ごとに項目があり、最後のセルがヘッダー。
  Row 1: 馬番 (1-18)
  Row 35: スピード指数 (float値)
  馬名はRow 2にあるが「/」区切りで父馬も含むため切り出しが必要。
  エンコーディングはShift_JIS。
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
SOURCE_NAME = "jiro8-speed"
BASE_URL = "https://jiro8.sakura.ne.jp"
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 1.0

# タイムゾーン
JST = timezone(timedelta(hours=9))

# jiro8の競馬場コード（VENUE_CODE_MAPと同一だが名前→コードの逆引き用）
JIRO8_VENUE_CODE_MAP = {
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

# コード→名前の逆引き
VENUE_CODE_TO_NAME = {v: k for k, v in JIRO8_VENUE_CODE_MAP.items()}


def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("SPEED_INDICES_TABLE_NAME", "baken-kaigi-speed-indices")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def fetch_page(url: str) -> BeautifulSoup | None:
    """ページを取得してBeautifulSoupオブジェクトを返す.

    jiro8はShift_JISエンコーディングのため、明示的にデコードする。
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BakenKaigiBot/1.0; +https://bakenkaigi.com)",
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        # Shift_JISでデコード
        response.encoding = "shift_jis"
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def find_venue_codes_for_date(soup: BeautifulSoup, target_date: str) -> list[dict]:
    """トップページから対象日付の競馬場コードを取得.

    サイドバーの開催日付リストから、対象日付に対応するリンクを探す。
    リンクは index.php?code=YYVVRRDDNN 形式。

    Args:
        soup: トップページのBeautifulSoup
        target_date: 対象日付 (例: "2/8")

    Returns:
        list of dict: [{"venue": "東京", "venue_code": "05", "kai": "01", "nichi": "04"}, ...]
    """
    venues = []

    # トップページから全リンクを検索
    for link in soup.find_all("a", href=re.compile(r"index\.php\?code=\d{10}")):
        href = link.get("href", "")
        # codeパラメータを抽出
        match = re.search(r"code=(\d{10})", href)
        if not match:
            continue

        code = match.group(1)
        # YYVVRRDDNN を分解
        venue_code = code[2:4]
        kai = code[4:6]
        nichi = code[6:8]
        race_num = code[8:10]

        # 競馬場名を取得
        venue_name = VENUE_CODE_TO_NAME.get(venue_code)
        if not venue_name:
            continue

        # 999999 は一覧ページなのでスキップ
        if kai == "99" or nichi == "99":
            continue

        # レース番号11のリンク（メインのナビリンク）を探す
        # サイドバーの開催日付欄に日付テキストがあるかチェック
        parent = link.find_parent("td")
        if parent:
            parent_text = parent.get_text()
            # "2/8" のような日付パターンを含むか
            if target_date in parent_text:
                venue_info = {
                    "venue": venue_name,
                    "venue_code": venue_code,
                    "kai": kai,
                    "nichi": nichi,
                }
                # 重複を避ける
                if venue_info not in venues:
                    venues.append(venue_info)

    # サイドバーで見つからない場合、太字(b)テキストからも探す
    if not venues:
        for bold in soup.find_all("b"):
            text = bold.get_text(strip=True)
            if target_date in text:
                # 同じtd内のリンクを探す
                parent = bold.find_parent("td")
                if parent:
                    for link in parent.find_all("a", href=re.compile(r"code=\d{10}")):
                        href = link.get("href", "")
                        match = re.search(r"code=(\d{10})", href)
                        if match:
                            code = match.group(1)
                            venue_code = code[2:4]
                            kai = code[4:6]
                            nichi = code[6:8]
                            venue_name = VENUE_CODE_TO_NAME.get(venue_code)
                            if venue_name and kai != "99" and nichi != "99":
                                venue_info = {
                                    "venue": venue_name,
                                    "venue_code": venue_code,
                                    "kai": kai,
                                    "nichi": nichi,
                                }
                                if venue_info not in venues:
                                    venues.append(venue_info)

    return venues


def parse_race_page(soup: BeautifulSoup) -> list[dict]:
    """レースページからスピード指数データを抽出.

    馬柱テーブルの構造:
    - 最後のセルがヘッダー（例: "馬番", "スピード指数"）
    - その前のセルが各馬のデータ（馬番順に右→左に並ぶ）

    Returns:
        list of dict: [{"horse_number": 1, "horse_name": "xxx", "speed_index": 85.5}, ...]
    """
    tables = soup.find_all("table")

    # 馬柱テーブルを探す: 多くのセルを持つテーブル
    main_table = None
    for table in tables:
        trs = table.find_all("tr", recursive=False)
        if len(trs) > 30:
            main_table = table
            break

    if not main_table:
        return []

    trs = main_table.find_all("tr", recursive=False)

    # データ行を特定
    horse_numbers = []
    horse_names = []
    speed_indices = []

    for tr in trs:
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue

        # 最後のセルがヘッダー
        header = tds[-1].get_text(strip=True)

        if header == "馬番":
            # 馬番行: 右から左に馬番が並ぶ（最後のセル=ヘッダーを除く）
            for td in tds[:-1]:
                text = td.get_text(strip=True)
                try:
                    horse_numbers.append(int(text))
                except ValueError:
                    horse_numbers.append(0)

        elif header == "馬名":
            # 馬名行: "馬名/父馬名母父馬名" の形式
            for td in tds[:-1]:
                text = td.get_text(strip=True)
                # "/"で区切り、最初の部分が馬名
                name = text.split("/")[0] if "/" in text else text
                # 半角カナを全角に変換し、ﾞﾟなどの濁点を処理
                horse_names.append(name.strip())

        elif header == "スピード指数":
            # スピード指数行
            for td in tds[:-1]:
                text = td.get_text(strip=True)
                try:
                    speed_indices.append(float(text))
                except ValueError:
                    speed_indices.append(0.0)

    if not horse_numbers or not speed_indices:
        return []

    # 馬番と指数を対応付ける
    # 馬柱は右→左に並んでいるため、reverse して馬番小→大にする
    horse_numbers = list(reversed(horse_numbers))
    speed_indices = list(reversed(speed_indices))
    if horse_names:
        horse_names = list(reversed(horse_names))

    results = []
    for i in range(min(len(horse_numbers), len(speed_indices))):
        hn = horse_numbers[i]
        si = speed_indices[i]

        if hn < 1 or hn > 18 or si <= 0:
            continue

        entry = {
            "horse_number": hn,
            "speed_index": si,
            "horse_name": horse_names[i] if i < len(horse_names) else "",
        }
        results.append(entry)

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
        "indices": indices,
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
    2. 各競馬場の各レース(1R-12R)ページをスクレイピング
    3. スピード指数を抽出してDynamoDBに保存
    """
    table = get_dynamodb_table()
    scraped_at = datetime.now(JST)
    tomorrow = scraped_at + timedelta(days=1)
    date_str = tomorrow.strftime("%Y%m%d")
    year_2digit = tomorrow.strftime("%y")
    target_date = f"{tomorrow.month}/{tomorrow.day}"

    results = {
        "success": True,
        "races_scraped": 0,
        "errors": [],
    }

    # Step 1: トップページから開催情報を取得
    logger.info(f"Fetching top page from {BASE_URL}")
    top_soup = fetch_page(BASE_URL)
    if not top_soup:
        results["success"] = False
        results["errors"].append("Failed to fetch top page")
        return results

    venues = find_venue_codes_for_date(top_soup, target_date)
    if not venues:
        logger.info(f"No venues found for {target_date}")
        results["races_scraped"] = 0
        return results

    logger.info(f"Found {len(venues)} venues for {target_date}: {venues}")

    # Step 2: 各レースページをスクレイピング
    for venue_info in venues:
        venue = venue_info["venue"]
        venue_code = venue_info["venue_code"]
        kai = venue_info["kai"]
        nichi = venue_info["nichi"]

        for race_number in range(1, 13):
            code = f"{year_2digit}{venue_code}{kai}{nichi}{race_number:02d}"
            race_url = f"{BASE_URL}/index.php?code={code}"

            logger.info(f"Scraping {venue} {race_number}R: {race_url}")
            time.sleep(REQUEST_DELAY_SECONDS)

            race_soup = fetch_page(race_url)
            if not race_soup:
                results["errors"].append(f"Failed to fetch {venue} {race_number}R")
                continue

            indices = parse_race_page(race_soup)
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
    logger.info(f"Starting jiro8 speed index scraper: event={event}")

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
