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
    "13": "芝",    # 芝・左外
    "14": "芝",    # 芝・右外回り
    "15": "芝",    # 芝・左内回り
    "16": "芝",    # 芝・右内回り
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
    "27": "ダ",    # ダート・左外
    "28": "ダ",    # ダート・右内回り
    "29": "ダ",    # ダート・その他
    "51": "障",    # 障害・芝
    "52": "障",    # 障害・ダート
    "53": "障",    # 障害・その他
}

# 種別コード → 馬齢条件
SYUBETU_CODES = {
    "11": "2歳",
    "12": "3歳",
    "13": "3歳以上",
    "14": "4歳以上",
    "18": "",        # 障害
    "19": "",        # 障害
    "99": "",        # その他
}

# 条件コード → クラス名
JYOKEN_CODES = {
    "701": "新馬",
    "702": "新馬",
    "703": "未勝利",
    "704": "1勝クラス",
    "705": "2勝クラス",
    "706": "3勝クラス",
    "999": "オープン",
    "700": "オープン",
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

        # レース名 (位置 32-92) - 本題（特別レース名）
        race_name = f"{venue_name} {int(race_num)}R"  # デフォルト
        if len(data) > 92:
            # 全角スペース(U+3000)を除去してレース名を取得
            hondai = data[32:92].strip().replace('\u3000', '')
            if hondai:
                race_name = hondai
            elif len(data) > 519:
                # 本題が空の場合（一般条件戦）は条件コードからレース名を生成
                # SyubetuCd (種別コード) - 位置 507-509: 馬齢条件
                syubetu_cd = data[507:509]
                syubetu_name = SYUBETU_CODES.get(syubetu_cd, "")

                # JyokenCd (条件コード) - 位置 516-519: クラス条件
                jyoken_cd = data[516:519]
                jyoken_name = JYOKEN_CODES.get(jyoken_cd, "")

                # 馬齢 + クラス でレース名を生成
                if syubetu_name and jyoken_name:
                    race_name = f"{syubetu_name}{jyoken_name}"
                elif jyoken_name:
                    race_name = jyoken_name
                elif syubetu_name:
                    race_name = f"{syubetu_name}条件"

        # 距離 (位置 558-562) - 実際のRAレコード解析により特定
        distance = 0
        if len(data) > 562:
            kyori_str = data[558:562]
            if kyori_str.strip().isdigit():
                distance = int(kyori_str.strip())

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
            "race_name": race_name,
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

        # [27:28] 枠番 (1桁)
        waku_str = data[27:28]
        if waku_str.isdigit():
            waku_ban = int(waku_str)
        else:
            waku_ban = 0

        # [28:30] 馬番 (2桁)
        umaban_str = data[28:30]
        if umaban_str.isdigit():
            horse_number = int(umaban_str)
        else:
            horse_number = 0

        # [30:39] 馬ID (9桁)
        horse_id = data[30:39].strip()

        # [40:58] 馬名 (18バイト = 全角9文字)
        horse_name = data[40:58].strip().replace('\u3000', '')

        # 騎手名 [192:200] (8バイト = 全角4文字)
        jockey_name = ""
        if len(data) > 200:
            jockey_name = data[192:200].strip().replace('\u3000', '')

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
            "waku_ban": waku_ban,
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


def parse_o1_record(data: str) -> list[dict] | None:
    """O1 レコードをパースして単勝オッズ情報のリストを返す.

    O1レコード構造:
    - [0:2]   RecordType: 'O1'
    - [11:19] RaceDate
    - [19:21] JyoCode
    - [21:23] Kai
    - [23:25] Nichiji
    - [25:27] RaceNum
    - [27:35] Header/Padding (8 bytes)
    - [35+]   各馬のオッズ情報 (8 bytes each):
              - [0:2] UmaBan (馬番)
              - [2:6] Odds (オッズ × 10)
              - [6:8] Ninki (人気)
    """
    try:
        if data[:2] != "O1":
            return None

        race_date = data[11:19]
        jyo_cd = data[19:21]
        kai = data[21:23]
        nichiji = data[23:25]
        race_num = data[25:27]

        race_id = f"{race_date}{jyo_cd}{kai}{nichiji}{race_num}"

        odds_list = []

        # 位置 35 から 8 バイトずつ読み込み（最大18頭）
        for i in range(18):
            start = 35 + i * 8
            end = start + 8

            if end > len(data):
                break

            chunk = data[start:end]

            # 馬番 (2 bytes)
            umaban_str = chunk[0:2]
            if not umaban_str.isdigit():
                continue

            horse_number = int(umaban_str)
            if horse_number < 1 or horse_number > 18:
                continue

            # オッズ (4 bytes) - 値は × 10 で格納
            odds_str = chunk[2:6]
            if not odds_str.isdigit():
                continue

            odds = int(odds_str) / 10.0

            # 人気 (2 bytes)
            ninki_str = chunk[6:8]
            if not ninki_str.isdigit():
                continue

            popularity = int(ninki_str)
            if popularity < 1 or popularity > 18:
                continue

            odds_list.append({
                "race_id": race_id,
                "horse_number": horse_number,
                "odds": odds,
                "popularity": popularity,
            })

        return odds_list if odds_list else None

    except Exception as e:
        logger.error(f"Failed to parse O1 record: {e}")
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
        odds_count = 0
        record_count = 0

        # O1 データを一時保存（SE レコードより先に来ることがあるため）
        pending_odds = []

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

            # O1 レコード（単勝オッズ情報）- 後で適用するため一時保存
            elif record_type == "O1":
                odds_list = parse_o1_record(data)
                if odds_list:
                    pending_odds.extend(odds_list)

            # 進捗表示
            if record_count % 1000 == 0:
                logger.info(f"Processed {record_count} records, {race_count} races")

        # オッズデータを適用（全ての SE レコード処理後）
        logger.info(f"Applying {len(pending_odds)} odds entries...")
        for odds_info in pending_odds:
            db.update_runner_odds(
                odds_info["race_id"],
                odds_info["horse_number"],
                odds_info["odds"],
                odds_info["popularity"]
            )
            odds_count += 1

        # 同期状態を更新
        if last_timestamp:
            db.update_sync_status(last_timestamp, record_count)

        jv.JVClose()
        logger.info(f"Sync completed: {record_count} records, {race_count} races, {runner_count} runners, {odds_count} odds")
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
