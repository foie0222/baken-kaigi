"""jiro8スピード指数バックフィルスクリプト.

DynamoDBのレースデータから過去の開催情報(kaisai_kai, kaisai_nichime)を取得し、
jiro8.sakura.ne.jpからスピード指数をスクレイプしてDynamoDBに保存する。

使い方:
    cd backend && uv run python -m scripts.backfill_jiro8_speed_indices [--dry-run]
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Attr

# jiro8スクレイパーの関数を再利用
from batch.jiro8_speed_index_scraper import (
    BASE_URL,
    JIRO8_VENUE_CODE_MAP,
    REQUEST_DELAY_SECONDS,
    SOURCE_NAME,
    fetch_page,
    generate_race_id,
    parse_race_page,
    save_indices,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

RACES_TABLE = "baken-kaigi-races"
SPEED_INDICES_TABLE = "baken-kaigi-speed-indices"


def get_race_dates_with_venues(dynamodb) -> dict[str, list[dict]]:
    """DynamoDBからレース日ごとの会場情報を取得する.

    Returns:
        {
            "20260104": [
                {"venue": "中山", "venue_code": "06", "kai": "01", "nichi": "01", "race_count": 12},
                {"venue": "京都", "venue_code": "08", "kai": "01", "nichi": "01", "race_count": 12},
            ],
            ...
        }
    """
    table = dynamodb.Table(RACES_TABLE)

    # 2026年のレースデータをスキャン
    response = table.scan(
        FilterExpression=Attr("race_date").begins_with("2026"),
        ProjectionExpression="race_date, venue, venue_code, kaisai_kai, kaisai_nichime, race_number",
    )
    items = response["Items"]
    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=Attr("race_date").begins_with("2026"),
            ProjectionExpression="race_date, venue, venue_code, kaisai_kai, kaisai_nichime, race_number",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response["Items"])

    # 日付×会場でグループ化
    date_venues: dict[str, dict[str, dict]] = {}
    for item in items:
        race_date = item["race_date"]
        venue_code = item["venue_code"]
        key = f"{race_date}_{venue_code}"

        if race_date not in date_venues:
            date_venues[race_date] = {}

        if venue_code not in date_venues[race_date]:
            date_venues[race_date][venue_code] = {
                "venue": item["venue"],
                "venue_code": venue_code,
                "kai": item.get("kaisai_kai", ""),
                "nichi": item.get("kaisai_nichime", ""),
                "race_count": 0,
            }

        date_venues[race_date][venue_code]["race_count"] += 1

    # dict → sorted list
    result = {}
    for date_str in sorted(date_venues.keys()):
        result[date_str] = sorted(
            date_venues[date_str].values(),
            key=lambda v: v["venue_code"],
        )

    return result


def get_existing_speed_indices(dynamodb, race_date: str) -> set[str]:
    """指定日の既存スピード指数のrace_idセットを取得."""
    table = dynamodb.Table(SPEED_INDICES_TABLE)

    response = table.scan(
        FilterExpression=Attr("race_id").begins_with(race_date) & Attr("source").eq(SOURCE_NAME),
        ProjectionExpression="race_id",
    )
    items = response["Items"]
    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=Attr("race_id").begins_with(race_date) & Attr("source").eq(SOURCE_NAME),
            ProjectionExpression="race_id",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response["Items"])

    return {item["race_id"] for item in items}


def backfill_date(
    dynamodb,
    race_date: str,
    venues: list[dict],
    dry_run: bool = False,
) -> dict:
    """1日分のjiro8スピード指数をバックフィル."""
    table = dynamodb.Table(SPEED_INDICES_TABLE)
    scraped_at = datetime.now(JST)
    year_2digit = race_date[2:4]

    # 既存データをチェック
    existing = get_existing_speed_indices(dynamodb, race_date)

    stats = {"scraped": 0, "skipped": 0, "errors": 0, "no_data": 0}

    for venue_info in venues:
        venue = venue_info["venue"]
        venue_code = venue_info["venue_code"]
        kai = venue_info["kai"]
        nichi = venue_info["nichi"]
        race_count = venue_info["race_count"]

        if not kai or not nichi:
            logger.warning(f"  {venue}: kaisai_kai/nichime が空のためスキップ")
            stats["errors"] += 1
            continue

        for race_number in range(1, race_count + 1):
            race_id = generate_race_id(race_date, venue, race_number)

            if race_id in existing:
                logger.info(f"  {venue} {race_number}R: 既存データあり、スキップ")
                stats["skipped"] += 1
                continue

            code = f"{year_2digit}{venue_code}{kai.zfill(2)}{nichi.zfill(2)}{race_number:02d}"
            race_url = f"{BASE_URL}/index.php?code={code}"

            if dry_run:
                logger.info(f"  [DRY RUN] {venue} {race_number}R: {race_url}")
                stats["scraped"] += 1
                continue

            logger.info(f"  {venue} {race_number}R: {race_url}")
            time.sleep(REQUEST_DELAY_SECONDS)

            race_soup = fetch_page(race_url)
            if not race_soup:
                logger.error(f"  {venue} {race_number}R: ページ取得失敗")
                stats["errors"] += 1
                continue

            indices = parse_race_page(race_soup)
            if not indices:
                logger.warning(f"  {venue} {race_number}R: スピード指数なし")
                stats["no_data"] += 1
                continue

            try:
                save_indices(
                    table=table,
                    race_id=race_id,
                    venue=venue,
                    race_number=race_number,
                    indices=indices,
                    scraped_at=scraped_at,
                )
                stats["scraped"] += 1
            except Exception as e:
                logger.error(f"  {venue} {race_number}R: 保存失敗 - {e}")
                stats["errors"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="jiro8スピード指数バックフィル")
    parser.add_argument("--dry-run", action="store_true", help="実際にスクレイプせずURLのみ表示")
    parser.add_argument("--date", type=str, help="特定の日付のみ処理 (YYYYMMDD)")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")

    logger.info("DynamoDBからレースデータを取得中...")
    date_venues = get_race_dates_with_venues(dynamodb)
    logger.info(f"  {len(date_venues)} 開催日が見つかりました")

    # 今日以前の日付のみ対象（未来のレースはスクレイプ不要）
    today_str = datetime.now(JST).strftime("%Y%m%d")

    total_stats = {"scraped": 0, "skipped": 0, "errors": 0, "no_data": 0}

    for race_date, venues in date_venues.items():
        if race_date > today_str:
            logger.info(f"\n{race_date}: 未来の日付のためスキップ")
            continue

        if args.date and race_date != args.date:
            continue

        venue_names = ", ".join(f"{v['venue']}({v['race_count']}R)" for v in venues)
        logger.info(f"\n{'='*60}")
        logger.info(f"{race_date}: {venue_names}")
        logger.info(f"{'='*60}")

        stats = backfill_date(dynamodb, race_date, venues, dry_run=args.dry_run)

        for k in total_stats:
            total_stats[k] += stats[k]

        logger.info(f"  結果: 取得={stats['scraped']}, スキップ={stats['skipped']}, "
                     f"データなし={stats['no_data']}, エラー={stats['errors']}")

    logger.info(f"\n{'='*60}")
    logger.info(f"合計: 取得={total_stats['scraped']}, スキップ={total_stats['skipped']}, "
                 f"データなし={total_stats['no_data']}, エラー={total_stats['errors']}")


if __name__ == "__main__":
    main()
