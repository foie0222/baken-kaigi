"""吉馬スピード指数バックフィルスクリプト.

DynamoDBのレースデータから過去の開催情報を取得し、
kichiuma.netからスピード指数をスクレイプしてDynamoDBに保存する。

使い方:
    cd backend && PYTHONPATH=. python3 -m scripts.backfill_kichiuma_speed_indices [--dry-run]
"""

import argparse
import logging
import time
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Attr

from batch.kichiuma_scraper import (
    BASE_URL,
    KICHIUMA_VENUE_ID_MAP,
    REQUEST_DELAY_SECONDS,
    SOURCE_NAME,
    VENUE_NAME_TO_KICHIUMA_ID,
    fetch_page,
    generate_race_id,
    parse_race_list,
    parse_speed_index_page,
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
    """DynamoDBからレース日ごとの会場情報を取得する."""
    table = dynamodb.Table(RACES_TABLE)

    response = table.scan(
        FilterExpression=Attr("race_date").begins_with("2026"),
        ProjectionExpression="race_date, venue, venue_code, race_number",
    )
    items = response["Items"]
    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=Attr("race_date").begins_with("2026"),
            ProjectionExpression="race_date, venue, venue_code, race_number",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response["Items"])

    # 日付×会場でグループ化
    date_venues: dict[str, dict[str, dict]] = {}
    for item in items:
        race_date = item["race_date"]
        venue = item["venue"]

        if race_date not in date_venues:
            date_venues[race_date] = {}

        if venue not in date_venues[race_date]:
            date_venues[race_date][venue] = {
                "venue": venue,
                "venue_code": item["venue_code"],
                "race_count": 0,
            }

        date_venues[race_date][venue]["race_count"] += 1

    result = {}
    for date_str in sorted(date_venues.keys()):
        result[date_str] = sorted(
            date_venues[date_str].values(),
            key=lambda v: v["venue_code"],
        )

    return result


def get_existing_speed_indices(dynamodb, race_date: str) -> set[str]:
    """指定日の既存吉馬スピード指数のrace_idセットを取得."""
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


def make_date_param(race_date: str) -> str:
    """YYYYMMDD → YYYY%2FM%2FD 形式に変換."""
    dt = datetime.strptime(race_date, "%Y%m%d")
    return f"{dt.year}%2F{dt.month}%2F{dt.day}"


def backfill_date(
    dynamodb,
    race_date: str,
    venues: list[dict],
    dry_run: bool = False,
) -> dict:
    """1日分の吉馬スピード指数をバックフィル."""
    table = dynamodb.Table(SPEED_INDICES_TABLE)
    scraped_at = datetime.now(JST)
    date_param = make_date_param(race_date)

    existing = get_existing_speed_indices(dynamodb, race_date)

    stats = {"scraped": 0, "skipped": 0, "errors": 0, "no_data": 0}

    for venue_info in venues:
        venue = venue_info["venue"]
        kichiuma_id = VENUE_NAME_TO_KICHIUMA_ID.get(venue)

        if not kichiuma_id:
            logger.warning(f"  {venue}: 吉馬IDが見つからないためスキップ")
            stats["errors"] += 1
            continue

        # 会場ページを取得してレース一覧を得る
        venue_url = f"{BASE_URL}/php/search.php?date={date_param}&id={kichiuma_id}"

        if dry_run:
            logger.info(f"  [DRY RUN] {venue} 会場ページ: {venue_url}")
            # ドライランでも会場ページをチェックして取得可能か確認
            race_count = venue_info["race_count"]
            for race_number in range(1, race_count + 1):
                race_id = generate_race_id(race_date, venue, race_number)
                if race_id in existing:
                    stats["skipped"] += 1
                else:
                    stats["scraped"] += 1
            continue

        logger.info(f"  {venue} 会場ページ取得: {venue_url}")
        time.sleep(REQUEST_DELAY_SECONDS)

        venue_soup = fetch_page(venue_url)
        if not venue_soup:
            logger.error(f"  {venue}: 会場ページ取得失敗")
            stats["errors"] += venue_info["race_count"]
            continue

        # タイトルにエラーが含まれる場合はスキップ
        title = venue_soup.find("title")
        if title and "エラー" in title.get_text():
            logger.warning(f"  {venue}: エラーページが返されました")
            stats["errors"] += venue_info["race_count"]
            continue

        races = parse_race_list(venue_soup, kichiuma_id, date_param)
        if not races:
            logger.warning(f"  {venue}: レース一覧が取得できません")
            stats["no_data"] += venue_info["race_count"]
            continue

        logger.info(f"  {venue}: {len(races)}レース検出")

        for race in races:
            race_number = race["race_number"]
            race_id = generate_race_id(race_date, venue, race_number)

            if race_id in existing:
                logger.info(f"  {venue} {race_number}R: 既存データあり、スキップ")
                stats["skipped"] += 1
                continue

            race_href = race["href"]
            sp_url = f"{BASE_URL}/php/{race_href}" if not race_href.startswith("http") else race_href
            if "../" in sp_url:
                sp_url = f"{BASE_URL}/{race_href.lstrip('../')}"

            logger.info(f"  {venue} {race_number}R: {sp_url}")
            time.sleep(REQUEST_DELAY_SECONDS)

            sp_soup = fetch_page(sp_url)
            if not sp_soup:
                logger.error(f"  {venue} {race_number}R: ページ取得失敗")
                stats["errors"] += 1
                continue

            indices = parse_speed_index_page(sp_soup)
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
    parser = argparse.ArgumentParser(description="吉馬スピード指数バックフィル")
    parser.add_argument("--dry-run", action="store_true", help="実際にスクレイプせずURL確認のみ")
    parser.add_argument("--date", type=str, help="特定の日付のみ処理 (YYYYMMDD)")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")

    logger.info("DynamoDBからレースデータを取得中...")
    date_venues = get_race_dates_with_venues(dynamodb)
    logger.info(f"  {len(date_venues)} 開催日が見つかりました")

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
