"""JV-Link データを SQLite に同期するバッチスクリプト.

Usage:
    python sync_jvlink.py              # 差分同期（前回の続きから）
    python sync_jvlink.py --full       # 全データ同期（最初から）
    python sync_jvlink.py --from 20250101  # 指定日から同期
"""
import argparse
import logging
import time
import sys

import win32com.client
import pythoncom

import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# 場所コード → 場所名
VENUE_NAMES = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}


def parse_ra_record(data: str) -> dict | None:
    """RA レコードをパースしてレース情報を返す."""
    try:
        if data[:2] != "RA":
            return None

        race_date = data[11:19]  # 開催日 YYYYMMDD
        jyo_cd = data[19:21]     # 場所コード
        kai = data[21:23]        # 開催回
        nichiji = data[23:25]    # 日目
        race_num = data[25:27]   # レース番号

        race_id = f"{race_date}{jyo_cd}{kai}{nichiji}{race_num}"
        venue_name = VENUE_NAMES.get(jyo_cd, "不明")

        return {
            "race_id": race_id,
            "race_date": race_date,
            "race_name": f"{venue_name} {int(race_num)}R",
            "race_number": int(race_num),
            "venue_code": jyo_cd,
            "venue_name": venue_name,
            "start_time": f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]} 12:00",
            "distance": 0,
            "track_type": "",
            "track_condition": "",
            "grade": "",
            "kai": kai,
            "nichiji": nichiji,
        }
    except Exception as e:
        logger.error(f"Failed to parse RA record: {e}")
        return None


def parse_se_record(data: str) -> dict | None:
    """SE レコードをパースして出走馬情報を返す."""
    try:
        if data[:2] != "SE":
            return None

        # SE レコードの構造（要調整）
        # 簡易的なパース
        race_date = data[11:19]
        jyo_cd = data[19:21]
        kai = data[21:23]
        nichiji = data[23:25]
        race_num = data[25:27]

        race_id = f"{race_date}{jyo_cd}{kai}{nichiji}{race_num}"

        # 馬番は位置を調整する必要があるかもしれない
        horse_number = int(data[27:29]) if data[27:29].strip().isdigit() else 0
        horse_name = data[29:65].strip() if len(data) > 65 else ""

        return {
            "race_id": race_id,
            "horse_number": horse_number,
            "horse_name": horse_name,
            "horse_id": "",
            "jockey_name": "",
            "jockey_id": "",
            "trainer_name": "",
            "weight": 0.0,
            "odds": None,
            "popularity": None,
        }
    except Exception as e:
        logger.error(f"Failed to parse SE record: {e}")
        return None


def sync_data(from_time: str = None, full_sync: bool = False):
    """JV-Link からデータを読み込んで SQLite に保存."""

    # DB 初期化
    db.init_db()

    # 同期状態を取得
    sync_status = db.get_sync_status()

    if full_sync:
        from_time = "00000000000000"
        logger.info("Full sync mode: starting from beginning")
    elif from_time:
        from_time = f"{from_time}000000"
        logger.info(f"Sync from specified date: {from_time}")
    else:
        from_time = sync_status.get("last_timestamp", "00000000000000")
        logger.info(f"Differential sync from: {from_time}")

    # COM 初期化
    pythoncom.CoInitialize()

    try:
        jv = win32com.client.Dispatch("JVDTLab.JVLink")
        result = jv.JVInit("BAKENKAIGI")
        if result != 0:
            logger.error(f"JVInit failed: {result}")
            return False

        logger.info("JV-Link initialized")

        # JVOpen
        open_result = jv.JVOpen("RACE", from_time, 1)
        logger.info(f"JVOpen result: {open_result}")

        if isinstance(open_result, tuple):
            status = open_result[0]
            total_count = open_result[1]
            last_timestamp = open_result[3] if len(open_result) > 3 else ""
        else:
            status = open_result
            total_count = 0
            last_timestamp = ""

        if status < 0:
            logger.error(f"JVOpen error: {status}")
            return False

        logger.info(f"Total files to process: {total_count}")

        # データ読み込み
        race_count = 0
        runner_count = 0
        record_count = 0

        while True:
            r = jv.JVRead("", 100000, "")
            read_status = r[0]

            if read_status == 0:  # EOF
                logger.info("Reached EOF")
                break

            if read_status == -1:  # ファイル切り替わり
                time.sleep(0.05)
                continue

            if read_status == -3:  # ダウンロード中
                logger.info("Waiting for download...")
                time.sleep(1)
                continue

            if read_status < 0:  # エラー
                logger.error(f"JVRead error: {read_status}")
                break

            record_count += 1
            data = r[1]
            record_type = data[:2]

            # RA レコード（レース情報）
            if record_type == "RA":
                race = parse_ra_record(data)
                if race:
                    db.upsert_race(race)
                    race_count += 1

            # SE レコード（出走馬情報）- 必要に応じて有効化
            # elif record_type == "SE":
            #     runner = parse_se_record(data)
            #     if runner:
            #         db.upsert_runner(runner)
            #         runner_count += 1

            # 進捗表示
            if record_count % 1000 == 0:
                logger.info(f"Processed {record_count} records, {race_count} races")

        # 同期状態を更新
        if last_timestamp:
            db.update_sync_status(last_timestamp, record_count)

        jv.JVClose()
        logger.info(f"Sync completed: {record_count} records, {race_count} races, {runner_count} runners")
        return True

    except Exception as e:
        logger.error(f"Sync error: {e}")
        return False
    finally:
        pythoncom.CoUninitialize()


def main():
    parser = argparse.ArgumentParser(description="Sync JV-Link data to SQLite")
    parser.add_argument("--full", action="store_true", help="Full sync from beginning")
    parser.add_argument("--from", dest="from_date", help="Sync from date (YYYYMMDD)")
    args = parser.parse_args()

    success = sync_data(
        from_time=args.from_date,
        full_sync=args.full
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
