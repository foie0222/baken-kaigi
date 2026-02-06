"""JRA出馬表チェックサム自動スクレイピング.

JRAサイトから出馬表ページをスクレイピングし、
全会場のbase_valueを自動取得してPostgreSQLに保存する。
"""

import logging
import time
from datetime import timedelta, timezone

import requests
from bs4 import BeautifulSoup

import database as db

logger = logging.getLogger(__name__)

# 定数
JRA_BASE_URL = "https://www.jra.go.jp/JRADB/accessD.html"
REQUEST_DELAY_SECONDS = 0.1
REQUEST_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (compatible; BakenKaigiBot/1.0; +https://bakenkaigi.com)"

JST = timezone(timedelta(hours=9))


def build_cname(venue_code: str, year: str, kaisai_kai: str, kaisai_nichime: int, race_number: int, date: str) -> str:
    """JRA出馬表のCNAMEパラメータを構築する.

    CNAME形式: pw01dde{01+venue}{year}{kai}{nichime}{race_number}{date}

    Args:
        venue_code: 競馬場コード（01-10）
        year: 年（4桁）
        kaisai_kai: 回次（01-05）
        kaisai_nichime: 日目（1-12）
        race_number: レース番号（1-12）
        date: 日付（YYYYMMDD形式）

    Returns:
        CNAME文字列
    """
    # venue部分: 01+venue_code (例: venue_code="05" → "0105")
    venue_part = f"01{venue_code}"
    return f"pw01dde{venue_part}{year}{kaisai_kai}{kaisai_nichime:02d}{race_number:02d}{date}"


def build_access_url(cname: str, checksum: int) -> str:
    """JRA出馬表のアクセスURLを構築する.

    Args:
        cname: CNAMEパラメータ
        checksum: チェックサム値（0-255）

    Returns:
        完全なURL
    """
    return f"{JRA_BASE_URL}?CNAME={cname}/{checksum:02X}"


def fetch_jra_page(url: str) -> requests.Response | None:
    """JRAページを取得する.

    Args:
        url: 取得するURL

    Returns:
        レスポンスオブジェクト、失敗時はNone
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.debug(f"Failed to fetch {url}: {e}")
        return None


def is_valid_race_page(html: str) -> bool:
    """正常な出馬表ページかどうかを判定する.

    パラメータエラーページでないことを確認する。

    Args:
        html: HTMLコンテンツ

    Returns:
        正常ページならTrue
    """
    return "パラメータエラー" not in html


def extract_checksums_from_nav(html: str) -> dict[str, int]:
    """ナビゲーションリンクから全会場の1Rチェックサムを抽出する.

    HTMLのナビゲーションから pw01dde で始まるCNAMEリンクを探し、
    各会場の1R（race_number="01"）のチェックサムを取得する。

    Args:
        html: 正常な出馬表ページのHTML

    Returns:
        {CNAME: checksum} の辞書
        例: {"pw01dde01052026010101020260207": 0xAB, ...}
    """
    soup = BeautifulSoup(html, "lxml")
    results = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "CNAME=pw01dde" not in href:
            continue

        # CNAME=pw01dde.../XX 形式からCNAMEとチェックサムを抽出
        try:
            cname_part = href.split("CNAME=")[1]
            parts = cname_part.split("/")
            if len(parts) != 2:
                continue
            cname = parts[0]
            checksum_hex = parts[1]
            checksum = int(checksum_hex, 16)
            results[cname] = checksum
        except (IndexError, ValueError):
            continue

    return results


def parse_cname(cname: str) -> dict | None:
    """CNAMEからレース情報を解析する.

    CNAME形式: pw01dde{4桁venue}{4桁year}{2桁kai}{2桁nichime}{2桁race}{8桁date}
    例: pw01dde01052026010101020260207

    Args:
        cname: CNAME文字列

    Returns:
        解析結果の辞書、不正な場合はNone
    """
    prefix = "pw01dde"
    if not cname.startswith(prefix):
        return None

    body = cname[len(prefix):]
    # 4(venue) + 4(year) + 2(kai) + 2(nichime) + 2(race) + 8(date) = 22
    if len(body) != 22:
        return None

    try:
        venue_part = body[0:4]  # "01XX"
        venue_code = venue_part[2:4]  # "XX"
        year = body[4:8]
        kaisai_kai = body[8:10]
        kaisai_nichime = int(body[10:12])
        race_number = int(body[12:14])
        date = body[14:22]

        return {
            "venue_code": venue_code,
            "year": year,
            "kaisai_kai": kaisai_kai,
            "kaisai_nichime": kaisai_nichime,
            "race_number": race_number,
            "date": date,
        }
    except (ValueError, IndexError):
        return None


def calculate_base_value(checksum_1r: int, kaisai_nichime: int) -> int:
    """1Rのチェックサムからbase_valueを逆算する.

    計算式: base_value = (checksum_1r - (nichime-1) * 48) % 256

    Args:
        checksum_1r: 1Rのチェックサム値
        kaisai_nichime: 日目（1-12）

    Returns:
        base_value（0-255）
    """
    return (checksum_1r - (kaisai_nichime - 1) * 48) % 256


def find_valid_checksum(venue_code: str, year: str, kaisai_kai: str, kaisai_nichime: int, date: str) -> tuple[str, int] | None:
    """有効なチェックサムをブルートフォースで探す.

    0-255のチェックサムを順に試行し、正常なページが返るものを見つける。

    Args:
        venue_code: 競馬場コード
        year: 年
        kaisai_kai: 回次
        kaisai_nichime: 日目
        date: 日付

    Returns:
        (HTMLコンテンツ, チェックサム) のタプル、見つからない場合はNone
    """
    cname = build_cname(venue_code, year, kaisai_kai, kaisai_nichime, 1, date)

    for checksum in range(256):
        url = build_access_url(cname, checksum)
        response = fetch_jra_page(url)

        if response and is_valid_race_page(response.text):
            logger.info(f"Found valid checksum {checksum:02X} for {cname}")
            return response.text, checksum

        if checksum < 255:
            time.sleep(REQUEST_DELAY_SECONDS)

    logger.warning(f"No valid checksum found for venue_code={venue_code}")
    return None


def scrape_jra_checksums(target_date: str) -> list[dict]:
    """JRAサイトから全会場のbase_valueを取得してDBに保存する.

    Args:
        target_date: 日付（YYYYMMDD形式）

    Returns:
        保存結果のリスト [{"venue_code": "05", "kaisai_kai": "01", "base_value": 123, "status": "saved"}, ...]
    """
    # 1. DBから当日の開催情報を取得
    kaisai_list = db.get_current_kaisai_info(target_date)
    if not kaisai_list:
        logger.info(f"No kaisai info found for {target_date}")
        return []

    logger.info(f"Found {len(kaisai_list)} venues for {target_date}: "
                f"{[k['venue_code'] for k in kaisai_list]}")

    year = target_date[:4]
    results = []

    # 2. 最初の会場で有効なチェックサムを探す
    first = kaisai_list[0]
    found = find_valid_checksum(
        venue_code=first["venue_code"],
        year=year,
        kaisai_kai=first["kaisai_kai"],
        kaisai_nichime=first["kaisai_nichime"],
        date=target_date,
    )

    if not found:
        logger.error("Failed to find valid checksum for any venue")
        return []

    html, _ = found

    # 3. ナビゲーションから全会場のチェックサムを抽出
    nav_checksums = extract_checksums_from_nav(html)
    logger.info(f"Extracted {len(nav_checksums)} CNAME checksums from navigation")

    # 4. 各会場の1Rチェックサムからbase_valueを計算して保存
    for kaisai in kaisai_list:
        venue_code = kaisai["venue_code"]
        kaisai_kai = kaisai["kaisai_kai"]
        kaisai_nichime = kaisai["kaisai_nichime"]

        # ナビゲーションから該当会場の1Rチェックサムを探す
        target_cname = build_cname(venue_code, year, kaisai_kai, kaisai_nichime, 1, target_date)
        checksum_1r = nav_checksums.get(target_cname)

        if checksum_1r is None:
            logger.warning(f"Checksum not found in nav for venue_code={venue_code}, "
                          f"kaisai_kai={kaisai_kai}")
            results.append({
                "venue_code": venue_code,
                "kaisai_kai": kaisai_kai,
                "base_value": None,
                "status": "not_found",
            })
            continue

        base_value = calculate_base_value(checksum_1r, kaisai_nichime)

        try:
            db.save_jra_checksum(venue_code, kaisai_kai, base_value)
            logger.info(f"Saved base_value={base_value} for venue_code={venue_code}, "
                       f"kaisai_kai={kaisai_kai}")
            results.append({
                "venue_code": venue_code,
                "kaisai_kai": kaisai_kai,
                "base_value": base_value,
                "status": "saved",
            })
        except Exception as e:
            logger.error(f"Failed to save checksum for venue_code={venue_code}: {e}")
            results.append({
                "venue_code": venue_code,
                "kaisai_kai": kaisai_kai,
                "base_value": base_value,
                "status": f"error: {e}",
            })

    return results
