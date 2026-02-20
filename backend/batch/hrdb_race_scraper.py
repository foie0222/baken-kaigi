"""HRDBレースデータバッチスクレイパー.

HRDB-APIからレース・出走馬データを取得し、DynamoDBに保存するLambdaハンドラー。
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3

from batch.hrdb_client import HrdbClient
from batch.hrdb_constants import VENUE_CODE_MAP, hrdb_to_race_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JST = timezone(timedelta(hours=9))
TTL_DAYS = 14

TRACK_TYPE_MAP = {
    "1": "芝",
    "2": "ダート",
    "5": "障害",
}


def _parse_run_time(runtm: str) -> str | None:
    """走破タイムを変換する.

    Args:
        runtm: HRDB形式のタイム (例: "1326")

    Returns:
        "M:SS.T" 形式の文字列。"0000"または空文字はNone。
    """
    if not runtm or runtm == "0000":
        return None
    # runtm = "1326" → 分=1, 秒=32, コンマ=6 → "1:32.6"
    minutes = int(runtm[0])
    seconds = int(runtm[1:3])
    tenths = int(runtm[3])
    return f"{minutes}:{seconds:02d}.{tenths}"


def convert_race_row(row: dict, scraped_at: datetime) -> dict:
    """RACEMSTのCSV行をDynamoDBアイテムに変換する."""
    opdt = row["OPDT"].strip()
    rcoursecd = row["RCOURSECD"].strip()
    rno = row["RNO"].strip()
    trackcd = row["TRACKCD"].strip()

    return {
        "race_date": opdt,
        "race_id": hrdb_to_race_id(opdt, rcoursecd, rno),
        "venue": VENUE_CODE_MAP[rcoursecd],
        "venue_code": rcoursecd,
        "race_number": int(rno),
        "race_name": row["RNMHON"].strip(),
        "grade": row["GCD"].strip(),
        "distance": int(row["DIST"].strip()),
        "track_type": TRACK_TYPE_MAP[trackcd[0]],
        "track_code": trackcd,
        "horse_count": int(row["ENTNUM"].strip()),
        "run_count": int(row["RUNNUM"].strip()),
        "post_time": row["POSTTM"].strip(),
        "weather_code": row["WEATHERCD"].strip(),
        "turf_condition_code": row["TSTATCD"].strip(),
        "dirt_condition_code": row["DSTATCD"].strip(),
        "kaisai_kai": row["KAI"].strip(),
        "kaisai_nichime": row["NITIME"].strip(),
        "scraped_at": scraped_at.isoformat(),
        "ttl": int((scraped_at + timedelta(days=TTL_DAYS)).timestamp()),
    }


def convert_runner_row(row: dict, scraped_at: datetime) -> dict:
    """RACEDTLのCSV行をDynamoDBアイテムに変換する."""
    opdt = row["OPDT"].strip()
    rcoursecd = row["RCOURSECD"].strip()
    rno = row["RNO"].strip()
    umano = row["UMANO"].strip()
    fixplc = row["FIXPLC"].strip()
    runtm = row["RUNTM"].strip()
    tanodds = row["TANODDS"].strip()
    tanninki = row["TANNINKI"].strip()
    ftnwght = row["FTNWGHT"].strip()

    item = {
        "race_id": hrdb_to_race_id(opdt, rcoursecd, rno),
        "horse_number": umano.zfill(2),
        "race_date": opdt,
        "horse_id": row["BLDNO"].strip(),
        "horse_name": row["HSNM"].strip(),
        "waku_ban": int(row["WAKNO"].strip()),
        "sex_code": row["SEXCD"].strip(),
        "age": int(row["AGE"].strip()),
        "jockey_id": row["JKYCD"].strip(),
        "jockey_name": row["JKYNM4"].strip(),
        "trainer_id": row["TRNRCD"].strip(),
        "trainer_name": row["TRNRNM4"].strip(),
        "weight_carried": Decimal(ftnwght) / 10,
        "finish_position": int(fixplc) if fixplc != "00" else None,
        "time": _parse_run_time(runtm),
        "odds": Decimal(tanodds) / 10 if tanodds != "0000" else None,
        "popularity": int(tanninki) if tanninki != "00" else None,
        "scraped_at": scraped_at.isoformat(),
        "ttl": int((scraped_at + timedelta(days=TTL_DAYS)).timestamp()),
    }

    # DynamoDBはNone値を受け付けないためフィルタ
    return {k: v for k, v in item.items() if v is not None}


def get_hrdb_client() -> HrdbClient:
    """Secrets ManagerからHRDB認証情報を取得してクライアントを生成."""
    sm = boto3.client("secretsmanager")
    secret = sm.get_secret_value(SecretId="baken-kaigi/gamble-os-credentials")
    creds = json.loads(secret["SecretString"])
    return HrdbClient(
        club_id=creds["club_id"],
        club_password=creds["club_password"],
    )


def get_races_table():
    """DynamoDB races テーブルを取得."""
    table_name = os.environ.get("RACES_TABLE_NAME", "baken-kaigi-races")
    return boto3.resource("dynamodb").Table(table_name)


def get_runners_table():
    """DynamoDB runners テーブルを取得."""
    table_name = os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners")
    return boto3.resource("dynamodb").Table(table_name)


def handler(event: dict, context) -> dict:
    """レースデータ取得Lambda ハンドラー."""
    offset_days = event.get("offset_days", 1)
    now = datetime.now(JST)
    target_date = (now + timedelta(days=offset_days)).strftime("%Y%m%d")
    scraped_at = now

    logger.info("Fetching HRDB race data for %s (offset_days=%d)", target_date, offset_days)

    client = get_hrdb_client()

    sql_race = f"SELECT * FROM RACEMST WHERE OPDT = '{target_date}';"
    sql_runner = f"SELECT * FROM RACEDTL WHERE OPDT = '{target_date}';"

    race_rows, runner_rows = client.query_dual(sql_race, sql_runner)

    races_table = get_races_table()
    runners_table = get_runners_table()

    races_saved = 0
    for row in race_rows:
        item = convert_race_row(row, scraped_at)
        races_table.put_item(Item=item)
        races_saved += 1

    runners_saved = 0
    for row in runner_rows:
        item = convert_runner_row(row, scraped_at)
        runners_table.put_item(Item=item)
        runners_saved += 1

    logger.info(
        "Saved %d races and %d runners for %s",
        races_saved,
        runners_saved,
        target_date,
    )

    return {
        "statusCode": 200,
        "body": {
            "success": True,
            "target_date": target_date,
            "races_saved": races_saved,
            "runners_saved": runners_saved,
        },
    }
