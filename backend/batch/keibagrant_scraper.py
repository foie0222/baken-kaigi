"""競馬グラント馬柱スクレイピング Lambda.

keibagrant.jp から馬柱PDF（出馬表）を取得し、テキスト変換してパースし、
馬ごとの近走成績・血統情報をDynamoDBに保存する。
"""

import io
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
import pdfplumber
import requests

from batch.ai_shisu_scraper import VENUE_CODE_MAP

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 定数
SOURCE_NAME = "keibagrant"
BASE_URL = "https://keibagrant.jp"
CATEGORY_URL = f"{BASE_URL}/?cat=6"  # JRA Race Card カテゴリ
TTL_DAYS = 7
REQUEST_DELAY_SECONDS = 1.0

# タイムゾーン
JST = timezone(timedelta(hours=9))



def get_dynamodb_table():
    """DynamoDB テーブルを取得."""
    table_name = os.environ.get("PAST_PERFORMANCES_TABLE_NAME", "baken-kaigi-past-performances")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def fetch_page(url: str):
    """HTMLページを取得してテキストを返す."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BakenKaigiBot/1.0; +https://bakenkaigi.com)",
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def fetch_pdf(url: str) -> str | None:
    """PDFをダウンロードしてテキストに変換."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BakenKaigiBot/1.0; +https://bakenkaigi.com)",
        }
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        text_parts = []
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(layout=True)
                if page_text:
                    text_parts.append(page_text)

        if not text_parts:
            logger.warning(f"No text extracted from PDF: {url}")
            return None

        return "\n".join(text_parts)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch PDF {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to convert PDF {url}: {e}")
        return None


def find_article_url(html: str, target_date: str) -> str | None:
    """カテゴリページから対象日付の記事URLを探す.

    Args:
        html: カテゴリページのHTML
        target_date: 対象日付 (例: "2月8日")

    Returns:
        str | None: 記事ページURL (例: "https://keibagrant.jp/?p=16206")
    """
    # entry-card-wrap リンクから日付を含む記事を探す
    # pattern: <a href="...?p=16206" ... title="2月8日（日） 1回東京4日...">
    pattern = re.compile(
        r'<a\s+href="([^"]+\?p=\d+)"[^>]*title="' + re.escape(target_date) + r'[^"]*\d+回[^"]*"'
    )
    match = pattern.search(html)
    if match:
        return match.group(1)
    return None


def parse_race_pdf_links(html: str) -> list[dict]:
    """記事ページからレースごとのPDFリンクを抽出.

    Returns:
        list of dict: [{"venue": "東京", "race_number": 1, "pdf_url": "..."}, ...]
    """
    races = []
    current_venue = None

    # <p> タグで競馬場名、<li> タグでレースリンクが並ぶ構造
    # 競馬場名: <p><a href="...pdf">1回東京4日</a></p>
    venue_pattern = re.compile(
        r'<p>\s*<a\s+href="[^"]+\.pdf"[^>]*>\s*\d+回(' + "|".join(VENUE_CODE_MAP.keys()) + r')\d+日\s*</a>\s*</p>'
    )
    # 個別レース: <li><a href="...pdf">11R</a>
    race_pattern = re.compile(
        r'<li>\s*<a\s+href="([^"]+\.pdf)"[^>]*>\s*(\d+)R\s*</a>'
    )

    lines = html.split("\n")
    for line in lines:
        venue_match = venue_pattern.search(line)
        if venue_match:
            current_venue = venue_match.group(1)
            continue

        if current_venue:
            race_match = race_pattern.search(line)
            if race_match:
                pdf_url = race_match.group(1)
                race_number = int(race_match.group(2))
                races.append({
                    "venue": current_venue,
                    "race_number": race_number,
                    "pdf_url": pdf_url,
                })

    return races



def _find_sire_line(lines: list[str], horse_line_idx: int, prev_horse_line_idx: int = 0) -> int | None:
    """馬名行から上方向に父行を探す.

    父行の特徴: 行頭にスペース、その後に馬名、「牡|牝|せん」+年齢パターン

    Args:
        lines: PDFテキストの全行
        horse_line_idx: 現在の馬名行インデックス
        prev_horse_line_idx: 前の馬名行インデックス（重複防止の下限）
    """
    # 前の馬ブロックとの境界を考慮
    # 前の馬名行の+4行目以降のみを検索範囲とする
    search_start = max(prev_horse_line_idx + 4, 0)

    for offset in range(1, 15):
        i = horse_line_idx - offset
        if i < search_start:
            break
        if re.search(r"(牡|牝|せん)\d+", lines[i]):
            return i
    return None


def _find_dam_sire_line(lines: list[str], horse_line_idx: int) -> int | None:
    """馬名行から下方向に母父行を探す.

    母父行の特徴: 行頭にスペース、(母父名) のパターン、距離・タイム情報
    """
    for offset in range(1, 5):
        i = horse_line_idx + offset
        if i >= len(lines):
            break
        if re.match(r"\s{8,}\(", lines[i]) and re.search(r"\d+m\s+", lines[i]):
            return i
    return None


def parse_horse_block(lines: list[str], horse_line_idx: int, prev_horse_line_idx: int = 0) -> dict | None:
    """馬名行を基点に動的にデータ行を探索して馬データを抽出.

    標準ブロック構造（前3行・後3行）:
    - 父行: 父名、性年齢、近走日付・競馬場
    - 騎手行: 騎手名、近走レース名
    - 母行: 母名、斤量、近走着順
    - 馬名行: 枠番・馬番・馬名、近走の騎手・斤量
    - 母父行: (母父名)、近走の距離・馬場・タイム

    外国馬や取消馬の影響で行がずれることがあるため、
    固定オフセットではなく動的探索で各行を特定する。
    """
    idx = horse_line_idx
    horse_line = lines[idx]

    # 馬番・馬名を抽出
    m = re.match(r"\s+(\d+)\s+(\d+)\s+[△◎○▲☆]*\d?\s*(\S+)", horse_line)
    if not m:
        return None

    horse_number = int(m.group(2))
    horse_name = m.group(3)

    # 父行を動的に探す（上方向）
    sire_line_idx = _find_sire_line(lines, idx, prev_horse_line_idx)
    sire = ""
    if sire_line_idx is not None:
        sire_match = re.match(r"\s{8,}(\S+)", lines[sire_line_idx])
        sire = sire_match.group(1) if sire_match else ""

    # 母行: 父行の2つ下（騎手行の次）
    dam = ""
    dam_line_idx = None
    if sire_line_idx is not None:
        dam_line_idx = sire_line_idx + 2
        if dam_line_idx < len(lines):
            dam_match = re.match(r"\s{8,}(\S+)", lines[dam_line_idx])
            dam = dam_match.group(1) if dam_match else ""

    # 母父行を動的に探す（下方向）
    dam_sire = ""
    dam_sire_line_idx = _find_dam_sire_line(lines, idx)
    if dam_sire_line_idx is not None:
        dam_sire_match = re.match(r"\s{8,}\((.+?)\)", lines[dam_sire_line_idx])
        if dam_sire_match:
            dam_sire = dam_sire_match.group(1)

    # 近走データの抽出
    past_races = _extract_past_races(lines, idx, sire_line_idx, dam_line_idx, dam_sire_line_idx)

    return {
        "horse_number": horse_number,
        "horse_name": horse_name,
        "sire": sire,
        "dam": dam,
        "dam_sire": dam_sire,
        "past_races": past_races,
    }


def _extract_past_races(
    lines: list[str],
    horse_line_idx: int,
    sire_line_idx: int | None,
    dam_line_idx: int | None,
    dam_sire_line_idx: int | None,
) -> list[dict]:
    """近走成績を抽出（最大5走）.

    各行のデータ:
    - 父行: 近走日付・競馬場
    - 騎手行（父行+1）: レース名
    - 母行（父行+2）: 着順
    - 馬名行: 騎手・斤量
    - 母父行: 距離・芝ダ・馬場・タイム
    """
    past_races = []
    horse_line = lines[horse_line_idx]

    if sire_line_idx is None or dam_sire_line_idx is None:
        return past_races

    sire_line = lines[sire_line_idx]
    jockey_line = lines[sire_line_idx + 1] if sire_line_idx + 1 < len(lines) else ""
    dam_sire_line = lines[dam_sire_line_idx]

    # 1. 日付・競馬場の抽出 (父行)
    # パターン: "25.11.23 98 10.5 4京都6"
    # 馬場差が「速」「遅」等になるケースにも対応
    date_venue_pairs = re.findall(
        r"(\d{2}\.\d{2}\.\d{2})\s+\d+\s+[\d.速遅平]+\s+\d?(" + "|".join(VENUE_CODE_MAP.keys()) + r")\d*",
        sire_line,
    )

    # 2. レース名の抽出 (騎手行)
    race_names = _extract_race_names(jockey_line)

    # 3. 着順の抽出 - 父行の下方で着順パターンを含む行を探す
    # パターン: "14  18頭 2番14人 最内"
    finish_entries = []
    for search_idx in range(sire_line_idx + 2, horse_line_idx):
        entries = re.findall(r"(\d+)\s+\d+頭\s*\d+番\s*\d+人", lines[search_idx])
        if entries:
            finish_entries = entries
            break

    # 4. 騎手・斤量の抽出 (馬名行)
    # パターン: "510 -6 坂井瑠 58" "516 +2 戸崎圭 58"
    # 斤量は 55, 56.0, 585(=58.5), 575(=57.5) のような表記
    jockey_weight_entries = re.findall(
        r"\d+\s+[+-]?\d+\s+(\S{2,4})\s+(\d{2,3})\s*\.?\s*[①-⑱]*",
        horse_line,
    )

    # 5. 距離・芝ダ・馬場・タイムの抽出 (母父行)
    # パターン: "1600m 芝C 良 1:32.6 34.0"
    time_entries = re.findall(
        r"(\d+)m\s+(芝|ダ)\w?\s+(良|稍|重|不)\s+(\d+:\d+\.\d+)\s+(\d+\.\d+)",
        dam_sire_line,
    )

    # 最大5走分を統合
    num_races = min(len(date_venue_pairs), len(time_entries), 5)

    for i in range(num_races):
        date_str_raw = date_venue_pairs[i][0]  # "25.11.23"
        venue = date_venue_pairs[i][1]  # "京都"

        # 日付変換: "25.11.23" -> "20251123"
        yy, mm, dd = date_str_raw.split(".")
        year = int(yy) + 2000
        date_str = f"{year}{mm}{dd}"

        distance = int(time_entries[i][0])
        track = time_entries[i][1]
        race_time = time_entries[i][3]

        # 着順
        finish_position = int(finish_entries[i]) if i < len(finish_entries) else 0

        # 騎手・斤量
        jockey = jockey_weight_entries[i][0] if i < len(jockey_weight_entries) else ""
        weight = _parse_weight(jockey_weight_entries[i][1]) if i < len(jockey_weight_entries) else 0.0

        # レース名
        race_name = race_names[i] if i < len(race_names) else ""

        past_race = {
            "date": date_str,
            "venue": venue,
            "race_name": race_name,
            "distance": distance,
            "track": track,
            "finish_position": finish_position,
            "time": race_time,
            "weight": weight,
            "jockey": jockey,
        }
        past_races.append(past_race)

    return past_races


def _parse_weight(weight_str: str) -> float:
    """斤量文字列をfloatに変換.

    PDFでは小数点が省略されることがある:
    - "58" -> 58.0
    - "585" -> 58.5 (3桁の場合は末尾1桁が小数)
    - "575" -> 57.5
    - "555" -> 55.5
    """
    val = int(weight_str)
    if val >= 100:
        # 3桁の場合: 585 -> 58.5
        return val / 10.0
    return float(val)


def _extract_race_names(jockey_line: str) -> list[str]:
    """騎手行からレース名を抽出.

    騎手行の近走部分には "マイルチャ GI" "富士Ｓ GII" のような
    レース名とグレードが並んでいる。
    """
    race_names = []

    # 千六/千ニ などの距離別成績の後に近走レース名が並ぶ
    parts_match = re.search(r"千[六ニ四八千二]\s+[\d.]+\s+(.*)", jockey_line)
    if not parts_match:
        return race_names

    race_section = parts_match.group(1)

    # グレードのパターン
    grade_pattern = r"(GI{1,3}|GIII|GII|GI|ｵｰﾌﾟﾝ|ﾘｽﾃｯﾄﾞ|\d勝ｸﾗｽ|未勝利)"

    # レース名とグレードのペアを抽出
    segments = re.split(r"\s{2,}", race_section.strip())

    current_name = ""
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        # グレード単独
        if re.match(grade_pattern + r"$", seg):
            if current_name:
                race_names.append(current_name)
                current_name = ""
        elif re.search(r"\d{2,3}\s+" + grade_pattern, seg):
            # "110 GII" のようなレーティング+グレードの場合
            name_part = re.sub(r"\s+\d{2,3}\s+" + grade_pattern, "", seg).strip()
            if name_part:
                race_names.append(name_part)
            elif current_name:
                race_names.append(current_name)
                current_name = ""
        else:
            # レース名
            grade_in = re.search(grade_pattern, seg)
            if grade_in:
                name_part = seg[:grade_in.start()].strip()
                if name_part:
                    race_names.append(name_part)
            else:
                current_name = seg

    if current_name and len(race_names) < 5:
        race_names.append(current_name)

    return race_names[:5]


def parse_pdf_horses(pdf_text: str) -> list[dict]:
    """PDFテキストから全出走馬のデータを抽出."""
    horses = []
    lines = pdf_text.split("\n")

    # 全馬名行のインデックスを先に収集
    horse_line_indices = []
    for i, line in enumerate(lines):
        m = re.match(r"\s+(\d+)\s+(\d+)\s+[△◎○▲☆]*\d?\s*(\S+)", line)
        if m and 1 <= int(m.group(2)) <= 18:
            horse_line_indices.append(i)

    # 各馬をパース
    for idx_pos, horse_idx in enumerate(horse_line_indices):
        prev_horse_idx = horse_line_indices[idx_pos - 1] if idx_pos > 0 else 0

        # ヘッダー行との区別: 上方向に父行（性年齢パターン）があるか確認
        sire_line_idx = _find_sire_line(lines, horse_idx, prev_horse_idx)
        if sire_line_idx is None:
            # 父行が見つからない場合は血統情報なしで基本データのみ抽出
            m = re.match(r"\s+(\d+)\s+(\d+)\s+[△◎○▲☆]*\d?\s*(\S+)", lines[horse_idx])
            if m:
                dam_sire_line_idx = _find_dam_sire_line(lines, horse_idx)
                dam_sire = ""
                if dam_sire_line_idx is not None:
                    dam_sire_match = re.match(r"\s{8,}\((.+?)\)", lines[dam_sire_line_idx])
                    if dam_sire_match:
                        dam_sire = dam_sire_match.group(1)
                horses.append({
                    "horse_number": int(m.group(2)),
                    "horse_name": m.group(3),
                    "sire": "",
                    "dam": "",
                    "dam_sire": dam_sire,
                    "past_races": [],
                })
            continue

        horse = parse_horse_block(lines, horse_idx, prev_horse_idx)
        if horse:
            horses.append(horse)

    return horses


def generate_race_id(date_str: str, venue: str, race_number: int) -> str:
    """JRA-VANスタイルのrace_idを生成."""
    venue_code = VENUE_CODE_MAP.get(venue, "00")
    return f"{date_str}{venue_code}{race_number:02d}"


def save_race_data(
    table,
    race_id: str,
    venue: str,
    race_number: int,
    horses: list[dict],
    scraped_at: datetime,
) -> None:
    """レースデータをDynamoDBに保存."""
    ttl = int((scraped_at + timedelta(days=TTL_DAYS)).timestamp())

    item = {
        "race_id": race_id,
        "source": SOURCE_NAME,
        "venue": venue,
        "race_number": race_number,
        "horses": horses,
        "scraped_at": scraped_at.isoformat(),
        "ttl": ttl,
    }

    table.put_item(Item=item)
    logger.info(f"Saved race data for {race_id}: {len(horses)} horses")


def scrape_races(offset_days: int = 1) -> dict[str, Any]:
    """メインのスクレイピング処理.

    Args:
        offset_days: 何日後のレースを取得するか。
            0 = 当日（レース当日の再取得用）
            1 = 翌日（前日夜の早期取得用、デフォルト）

    Returns:
        dict: {"success": bool, "races_scraped": int, "errors": list}
    """
    table = get_dynamodb_table()
    scraped_at = datetime.now(JST)
    target = scraped_at + timedelta(days=offset_days)
    date_str = target.strftime("%Y%m%d")
    target_date = f"{target.month}月{target.day}日"  # "2月8日" 形式

    results: dict[str, Any] = {
        "success": True,
        "races_scraped": 0,
        "errors": [],
    }

    # Step 1: カテゴリページから記事URLを取得
    logger.info(f"Fetching category page: {CATEGORY_URL}")
    cat_html = fetch_page(CATEGORY_URL)
    if not cat_html:
        results["success"] = False
        results["errors"].append("Failed to fetch category page")
        return results

    article_url = find_article_url(cat_html, target_date)
    if not article_url:
        logger.info(f"No article found for {target_date}")
        results["races_scraped"] = 0
        return results

    logger.info(f"Found article for {target_date}: {article_url}")

    # Step 2: 記事ページからPDFリンクを取得
    time.sleep(REQUEST_DELAY_SECONDS)
    article_html = fetch_page(article_url)
    if not article_html:
        results["success"] = False
        results["errors"].append(f"Failed to fetch article: {article_url}")
        return results

    race_links = parse_race_pdf_links(article_html)
    if not race_links:
        results["errors"].append("No race PDF links found")
        return results

    logger.info(f"Found {len(race_links)} race PDFs")

    # Step 3: 各PDFをダウンロード・パース・保存
    for race_info in race_links:
        pdf_url = race_info["pdf_url"]
        venue = race_info["venue"]
        race_number = race_info["race_number"]

        logger.info(f"Processing {venue} {race_number}R: {pdf_url}")
        time.sleep(REQUEST_DELAY_SECONDS)

        pdf_text = fetch_pdf(pdf_url)
        if not pdf_text:
            results["errors"].append(f"Failed to fetch PDF: {venue} {race_number}R")
            continue

        horses = parse_pdf_horses(pdf_text)
        if not horses:
            results["errors"].append(f"No horse data found: {venue} {race_number}R")
            continue

        race_id = generate_race_id(date_str, venue, race_number)

        try:
            save_race_data(
                table=table,
                race_id=race_id,
                venue=venue,
                race_number=race_number,
                horses=horses,
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
    logger.info(f"Starting keibagrant scraper: event={event}")

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
