"""PC-KEIBA Database (PostgreSQL) データアクセス層.

PC-KEIBA Database から直接レース・出走馬・血統情報を取得する。
pg8000 (pure Python PostgreSQL driver) を使用。
"""
import logging
import os
from contextlib import contextmanager
from datetime import datetime

import pg8000

logger = logging.getLogger(__name__)

# PC-KEIBA Database 接続設定
DB_CONFIG = {
    "host": os.environ.get("PCKEIBA_HOST", "localhost"),
    "port": int(os.environ.get("PCKEIBA_PORT", "5432")),
    "database": os.environ.get("PCKEIBA_DATABASE", "postgres"),
    "user": os.environ.get("PCKEIBA_USER", "postgres"),
}

# 競馬場コード → 名前のマッピング
VENUE_CODE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}


@contextmanager
def get_db():
    """DB 接続のコンテキストマネージャー."""
    password = os.environ.get("PCKEIBA_PASSWORD")
    if password is None:
        raise EnvironmentError(
            "PCKEIBA_PASSWORD environment variable is required. "
            "Please set it before running the application."
        )

    conn = None
    try:
        conn = pg8000.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=password,
        )
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def _fetch_all_as_dicts(cursor) -> list[dict]:
    """カーソル結果を辞書のリストとして取得."""
    if cursor.description is None:
        return []
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_one_as_dict(cursor) -> dict | None:
    """カーソルから1行を辞書として取得."""
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def init_db():
    """DB 初期化（PC-KEIBA では不要だが互換性のため残す）."""
    logger.info("Using PC-KEIBA Database - no initialization needed")


def _make_race_id(kaisai_nen: str, kaisai_tsukihi: str, keibajo_code: str, race_bango: str) -> str:
    """レースIDを生成する."""
    return f"{kaisai_nen}{kaisai_tsukihi}_{keibajo_code}_{race_bango}"


def _parse_race_id(race_id: str) -> tuple[str, str, str, str]:
    """レースIDをパースして (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango) を返す."""
    # Format: YYYYMMDD_XX_RR
    parts = race_id.split("_")
    if len(parts) != 3:
        raise ValueError(f"Invalid race_id format: {race_id}")
    date_str = parts[0]  # YYYYMMDD
    keibajo_code = parts[1]  # XX
    race_bango = parts[2]  # RR
    kaisai_nen = date_str[:4]
    kaisai_tsukihi = date_str[4:8]
    return kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango


def _validate_date(date: str) -> tuple[str, str]:
    """日付文字列を検証して (kaisai_nen, kaisai_tsukihi) を返す.

    Args:
        date: 日付（YYYYMMDD形式）

    Returns:
        (kaisai_nen, kaisai_tsukihi) のタプル

    Raises:
        TypeError: dateが文字列でない場合
        ValueError: dateが8桁でない、または不正な日付の場合
    """
    if not isinstance(date, str):
        raise TypeError("date must be a str in YYYYMMDD format")

    date_str = date.strip()

    if len(date_str) != 8 or not date_str.isdigit():
        raise ValueError("date must be an 8-digit string in YYYYMMDD format")

    # 実在する日付かを検証
    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(
            "date must represent a valid calendar date in YYYYMMDD format"
        ) from exc

    return date_str[:4], date_str[4:8]


def get_races_by_date(date: str) -> list[dict]:
    """指定日のレース一覧を取得.

    Args:
        date: 日付（YYYYMMDD形式）

    Raises:
        TypeError: dateが文字列でない場合
        ValueError: dateが不正な形式の場合
    """
    kaisai_nen, kaisai_tsukihi = _validate_date(date)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                kaisai_nen,
                kaisai_tsukihi,
                keibajo_code,
                race_bango,
                kyosomei_hondai,
                kyosomei_fukudai,
                grade_code,
                kyori,
                track_code,
                babajotai_code_shiba,
                babajotai_code_dirt,
                hasso_jikoku,
                shusso_tosu
            FROM jvd_ra
            WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
            ORDER BY keibajo_code, race_bango::integer
        """, (kaisai_nen, kaisai_tsukihi))
        rows = _fetch_all_as_dicts(cur)
        return [_to_race_dict(row) for row in rows]


def get_race_by_id(race_id: str) -> dict | None:
    """レース詳細を取得.

    Args:
        race_id: レースID（YYYYMMDD_XX_RR形式）
    """
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return None

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                kaisai_nen,
                kaisai_tsukihi,
                keibajo_code,
                race_bango,
                kyosomei_hondai,
                kyosomei_fukudai,
                grade_code,
                kyori,
                track_code,
                babajotai_code_shiba,
                babajotai_code_dirt,
                hasso_jikoku,
                shusso_tosu
            FROM jvd_ra
            WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
              AND keibajo_code = %s AND race_bango = %s
        """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
        row = _fetch_one_as_dict(cur)
        return _to_race_dict(row) if row else None


def get_runners_by_race(race_id: str) -> list[dict]:
    """出走馬一覧を取得.

    Args:
        race_id: レースID（YYYYMMDD_XX_RR形式）
    """
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return []

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                umaban,
                wakuban,
                bamei,
                ketto_toroku_bango,
                kishumei_ryakusho,
                kishu_code,
                chokyoshimei_ryakusho,
                futan_juryo,
                bataiju,
                zogen_sa,
                tansho_odds,
                tansho_ninkijun
            FROM jvd_se
            WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
              AND keibajo_code = %s AND race_bango = %s
            ORDER BY umaban::integer
        """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
        rows = _fetch_all_as_dicts(cur)
        return [_to_runner_dict(row) for row in rows]


def get_horse_count(race_id: str) -> int:
    """レースの出走馬数を取得."""
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return 0

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*)
            FROM jvd_se
            WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
              AND keibajo_code = %s AND race_bango = %s
        """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
        row = cur.fetchone()
        return row[0] if row else 0


def get_horse_counts_by_date(date: str) -> dict[str, int]:
    """指定日のレースごとの出走馬数を取得.

    Raises:
        TypeError: dateが文字列でない場合
        ValueError: dateが不正な形式の場合
    """
    kaisai_nen, kaisai_tsukihi = _validate_date(date)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                keibajo_code,
                race_bango,
                COUNT(*) as count
            FROM jvd_se
            WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
            GROUP BY keibajo_code, race_bango
        """, (kaisai_nen, kaisai_tsukihi))
        rows = _fetch_all_as_dicts(cur)

        result = {}
        for row in rows:
            race_id = _make_race_id(kaisai_nen, kaisai_tsukihi,
                                    row["keibajo_code"], row["race_bango"])
            result[race_id] = row["count"]
        return result


def get_horse_pedigree(horse_id: str) -> dict | None:
    """馬の血統情報を取得."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                ketto_toroku_bango AS horse_id,
                bamei AS horse_name,
                ketto_joho_01b AS sire_name,
                ketto_joho_02b AS dam_name,
                ketto_joho_05b AS broodmare_sire
            FROM jvd_um
            WHERE ketto_toroku_bango = %s
        """, (horse_id,))
        return _fetch_one_as_dict(cur)


def get_horse_weight_history(horse_id: str, limit: int = 5) -> list[dict]:
    """馬の体重履歴を取得."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                se.bataiju AS weight,
                se.zogen_sa AS weight_diff,
                se.kaisai_nen || se.kaisai_tsukihi AS race_date,
                ra.kyosomei_hondai AS race_name
            FROM jvd_se se
            JOIN jvd_ra ra ON
                se.kaisai_nen = ra.kaisai_nen AND
                se.kaisai_tsukihi = ra.kaisai_tsukihi AND
                se.keibajo_code = ra.keibajo_code AND
                se.race_bango = ra.race_bango
            WHERE se.ketto_toroku_bango = %s
              AND se.bataiju IS NOT NULL
              AND se.bataiju != ''
            ORDER BY se.kaisai_nen DESC, se.kaisai_tsukihi DESC
            LIMIT %s
        """, (horse_id, limit))
        rows = _fetch_all_as_dicts(cur)

        results = []
        for row in rows:
            try:
                weight = int(row["weight"]) if row["weight"] else 0
                weight_diff_str = str(row["weight_diff"] or "0").strip()
                try:
                    weight_diff = int(weight_diff_str)
                except (ValueError, TypeError):
                    weight_diff = 0
                results.append({
                    "weight": weight,
                    "weight_diff": weight_diff,
                    "race_date": row["race_date"],
                    "race_name": row["race_name"],
                })
            except (ValueError, TypeError):
                continue
        return results


def get_race_weights(race_id: str) -> list[dict]:
    """レースの馬体重情報を取得."""
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return []

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                umaban AS horse_number,
                bataiju AS weight,
                zogen_sa AS weight_diff
            FROM jvd_se
            WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
              AND keibajo_code = %s AND race_bango = %s
            ORDER BY umaban::integer
        """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
        rows = _fetch_all_as_dicts(cur)

        results = []
        for row in rows:
            try:
                horse_number = int(row["horse_number"]) if row["horse_number"] else 0
                weight = int(row["weight"]) if row["weight"] else 0
                weight_diff_str = str(row["weight_diff"] or "0").strip()
                try:
                    weight_diff = int(weight_diff_str)
                except (ValueError, TypeError):
                    weight_diff = 0
                results.append({
                    "horse_number": horse_number,
                    "weight": weight,
                    "weight_diff": weight_diff,
                })
            except (ValueError, TypeError):
                continue
        return results


def get_sync_status() -> dict:
    """同期状態を取得（互換性のため）."""
    with get_db() as conn:
        cur = conn.cursor()
        # 最新のレース日付を取得
        cur.execute("""
            SELECT
                MAX(kaisai_nen || kaisai_tsukihi) as last_date,
                COUNT(*) as record_count
            FROM jvd_ra
        """)
        row = _fetch_one_as_dict(cur)
        return {
            "last_timestamp": row["last_date"] if row else None,
            "last_sync_at": datetime.now().isoformat(),
            "record_count": row["record_count"] if row else 0,
        }


def _to_race_dict(row: dict) -> dict:
    """jvd_ra の行をレース辞書に変換."""
    if not row:
        return {}

    kaisai_nen = row.get("kaisai_nen", "")
    kaisai_tsukihi = row.get("kaisai_tsukihi", "")
    keibajo_code = row.get("keibajo_code", "")
    race_bango = row.get("race_bango", "")

    race_id = _make_race_id(kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango)
    venue_name = VENUE_CODE_MAP.get(keibajo_code, keibajo_code)

    # トラックコードの解釈
    track_code = row.get("track_code", "") or ""
    track_type = "芝" if track_code.startswith("1") else "ダート" if track_code.startswith("2") else ""

    # 馬場状態コードの解釈（芝/ダートで分岐）
    if track_code.startswith("1"):
        baba_cd = row.get("babajotai_code_shiba", "") or ""
    else:
        baba_cd = row.get("babajotai_code_dirt", "") or ""
    baba_map = {"1": "良", "2": "稍重", "3": "重", "4": "不良"}
    track_condition = baba_map.get(baba_cd, "")

    # レース名の組み立て
    race_name = (row.get("kyosomei_hondai", "") or "").strip()
    subtitle = (row.get("kyosomei_fukudai", "") or "").strip()
    full_race_name = f"{race_name} {subtitle}".strip() if subtitle else race_name

    # グレードコードの解釈
    grade_cd = row.get("grade_code", "") or ""
    grade_map = {"A": "G1", "B": "G2", "C": "G3", "D": "リステッド", "E": "オープン"}
    grade = grade_map.get(grade_cd, "")

    # 発走時刻
    hasso_jikoku = row.get("hasso_jikoku", "") or ""
    start_time = None
    if hasso_jikoku and len(hasso_jikoku) >= 4:
        try:
            hour = int(hasso_jikoku[:2])
            minute = int(hasso_jikoku[2:4])
            start_time = f"{kaisai_nen}-{kaisai_tsukihi[:2]}-{kaisai_tsukihi[2:]}T{hour:02d}:{minute:02d}:00"
        except (ValueError, IndexError) as exc:
            # 発走時刻の形式が不正な場合はログに記録し、開始時刻は未設定（None）のままとする
            logger.warning(
                "Invalid hasso_jikoku format: %s (race_id=%s): %s",
                hasso_jikoku,
                race_id,
                exc,
            )

    # 距離
    try:
        distance = int(row.get("kyori", 0) or 0)
    except (ValueError, TypeError):
        distance = 0

    return {
        "race_id": race_id,
        "race_date": f"{kaisai_nen}{kaisai_tsukihi}",
        "race_name": full_race_name,
        "race_number": int(race_bango) if race_bango.isdigit() else 0,
        "venue_code": keibajo_code,
        "venue_name": venue_name,
        "start_time": start_time,
        "distance": distance,
        "track_type": track_type,
        "track_condition": track_condition,
        "grade": grade,
    }


def _to_runner_dict(row: dict) -> dict:
    """jvd_se の行を出走馬辞書に変換."""
    if not row:
        return {}

    try:
        horse_number = int(row.get("umaban", 0) or 0)
    except (ValueError, TypeError):
        horse_number = 0

    try:
        waku_ban = int(row.get("wakuban", 0) or 0)
    except (ValueError, TypeError):
        waku_ban = 0

    try:
        weight_str = row.get("futan_juryo", "") or ""
        # 斤量は "560" のように10倍で格納されている場合がある
        if str(weight_str).isdigit():
            weight = float(weight_str) / 10 if len(str(weight_str)) == 3 else float(weight_str)
        else:
            weight = 0.0
    except (ValueError, TypeError):
        weight = 0.0

    # オッズ
    try:
        odds_str = row.get("tansho_odds", "") or ""
        if str(odds_str).isdigit():
            odds = float(odds_str) / 10  # 10倍で格納されている
        else:
            odds = None
    except (ValueError, TypeError):
        odds = None

    # 人気
    try:
        popularity_str = row.get("tansho_ninkijun", "") or ""
        popularity = int(popularity_str) if str(popularity_str).isdigit() else None
    except (ValueError, TypeError):
        popularity = None

    return {
        "horse_number": horse_number,
        "waku_ban": waku_ban,
        "horse_name": (row.get("bamei", "") or "").strip(),
        "horse_id": row.get("ketto_toroku_bango", "") or "",
        "jockey_name": (row.get("kishumei_ryakusho", "") or "").strip(),
        "jockey_id": row.get("kishu_code", "") or "",
        "trainer_name": (row.get("chokyoshimei_ryakusho", "") or "").strip(),
        "weight": weight,
        "odds": odds,
        "popularity": popularity,
    }


def check_connection() -> bool:
    """DB 接続確認."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Checking PC-KEIBA Database connection...")
    if check_connection():
        print("Connection OK!")

        # サンプルクエリ
        status = get_sync_status()
        print(f"\nDatabase status: {status}")

        # 最新のレースを取得
        if status.get("last_timestamp"):
            latest_date = status["last_timestamp"]
            print(f"\nRaces on {latest_date}:")
            races = get_races_by_date(latest_date)
            for r in races[:5]:
                print(f"  {r['venue_name']} {r['race_number']}R: {r['race_name']}")
    else:
        print("Connection FAILED!")
