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


# トラックコード → トラックタイプ
TRACK_TYPES = {
    "00": "",      # 不明
    "10": "芝",    # 芝・直線
    "11": "芝",    # 芝・左
    "12": "芝",    # 芝・右
    "17": "芝",    # 芝・左内
    "18": "芝",    # 芝・右内
    "19": "芝",    # 芝・右外
    "20": "ダ",    # ダート・直線
    "21": "ダ",    # ダート・左
    "22": "ダ",    # ダート・右
    "23": "ダ",    # ダート・左内
    "24": "ダ",    # ダート・右外
    "25": "ダ",    # ダート・外
    "26": "ダ",    # ダート・内
    "29": "ダ",    # ダート・その他
    "51": "障",    # 障害・芝
    "52": "障",    # 障害・ダート
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

        # 距離 (位置 593-597)
        distance = 0
        if len(data) > 597:
            kyori_str = data[593:597]
            if kyori_str.isdigit():
                distance = int(kyori_str)

        # トラックコード (位置 507-509)
        track_type = ""
        if len(data) > 509:
            track_cd = data[507:509]
            track_type = TRACK_TYPES.get(track_cd, "")

        # 発走時刻 (位置 734-738 - HHMM形式)
        start_hour = 12
        start_min = 0
        if len(data) > 738:
            hasso_str = data[734:738]
            if hasso_str.isdigit():
                hh = int(hasso_str[:2])
                mm = int(hasso_str[2:])
                if 6 <= hh <= 18 and 0 <= mm <= 59:
                    start_hour = hh
                    start_min = mm

        return {
            "race_id": race_id,
            "race_date": race_date,
            "race_name": f"{venue_name} {int(race_num)}R",
            "race_number": int(race_num),
            "venue_code": jyo_cd,
            "venue_name": venue_name,
            "start_time": f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]} {start_hour:02d}:{start_min:02d}",
            "distance": distance,
            "track_type": track_type,
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

        race_date = data[11:19]
        jyo_cd = data[19:21]
        kai = data[21:23]
        nichiji = data[23:25]
        race_num = data[25:27]

        race_id = f"{race_date}{jyo_cd}{kai}{nichiji}{race_num}"

        # [27:29] 枠番, [29:31] 馬番（2桁だが先頭1桁が馬番、10以上は2桁）
        umaban_str = data[29:31]
        if umaban_str.isdigit():
            # 02 -> 10, 12 -> 1, 22 -> 2, etc.
            first = int(umaban_str[0])
            second = int(umaban_str[1])
            if first == 0:
                horse_number = 10 + second  # 02 -> 12? 実際は10番台
            else:
                horse_number = first
        else:
            horse_number = 0

        # [31:40] 馬ID (9桁)
        horse_id = data[31:40].strip()

        # [40:58] 馬名 (18バイト = 全角9文字)
        horse_name = data[40:58].strip().replace('\u3000', '')

        # 騎手名を探す [72:92] 付近
        jockey_name = ""
        if len(data) > 92:
            jockey_area = data[72:92]
            for c in jockey_area:
                if ord(c) >= 0x3000 and c != '\u3000':
                    jockey_name += c
                elif jockey_name:
                    break

        # 斤量を探す [150:220] の範囲で 480-650 (48.0-65.0kg)
        weight = 0.0
        for pos in range(150, min(220, len(data) - 2)):
            chunk = data[pos:pos+3]
            if chunk.isdigit():
                val = int(chunk)
                if 480 <= val <= 650:
                    weight = val / 10.0
                    break

        return {
            "race_id": race_id,
            "horse_number": horse_number,
            "horse_name": horse_name,
            "horse_id": horse_id,
            "jockey_name": jockey_name,
            "jockey_id": "",
            "trainer_name": "",
            "weight": weight,
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

            # SE レコード（出走馬情報）
            elif record_type == "SE":
                runner = parse_se_record(data)
                if runner and runner["horse_number"] > 0:
                    db.upsert_runner(runner)
                    runner_count += 1

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
