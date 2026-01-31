"""PC-KEIBA Database (PostgreSQL) データアクセス層.

PC-KEIBA Database から直接レース・出走馬・血統情報を取得する。
pg8000 (pure Python PostgreSQL driver) を使用。
"""
import logging
import os
from contextlib import contextmanager
from datetime import datetime

from pathlib import Path
from dotenv import load_dotenv
import pg8000

# .env ファイルから環境変数を読み込み（このファイルと同じディレクトリ）
load_dotenv(Path(__file__).parent / ".env")

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

# 脚質コード → 名前のマッピング
RUNNING_STYLE_MAP = {
    "1": "逃げ",
    "2": "先行",
    "3": "差し",
    "4": "追込",
    "5": "自在",
    "": "不明",
}

# 競走種別コード → 年齢条件のマッピング（共通定数）
AGE_CONDITION_MAP = {
    "11": "2歳",
    "12": "3歳",
    "13": "3歳以上",
    "14": "4歳以上",
}

# 競走条件コード → クラスのマッピング（共通定数）
# 表示用とAPI用で異なる場合は display/api を分けて定義
RACE_CLASS_MAP = {
    "701": {"api": "新馬", "display": "新馬"},
    "702": {"api": "未出走", "display": "未出走"},
    "703": {"api": "未勝利", "display": "未勝利"},
    "005": {"api": "1勝", "display": "1勝クラス"},
    "010": {"api": "2勝", "display": "2勝クラス"},
    "016": {"api": "3勝", "display": "3勝クラス"},
    "999": {"api": "OP", "display": "オープン"},
}

# グレードコード → クラス名のマッピング（重賞・リステッド）
GRADE_CODE_MAP = {"A": "G1", "B": "G2", "C": "G3", "D": "L", "E": "OP"}


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
                shusso_tosu,
                kyoso_shubetsu_code,
                kyoso_joken_code,
                kaisai_kai,
                kaisai_nichime
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
                shusso_tosu,
                kyoso_shubetsu_code,
                kyoso_joken_code,
                kaisai_kai,
                kaisai_nichime
            FROM jvd_ra
            WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
              AND keibajo_code = %s AND race_bango = %s
        """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
        row = _fetch_one_as_dict(cur)
        return _to_race_dict(row) if row else None


def get_runners_by_race(race_id: str) -> list[dict]:
    """出走馬一覧を取得.

    オッズの優先順位:
    1. jvd_o1テーブルのリアルタイムオッズ（発売中オッズ）
    2. jvd_seテーブルの確定オッズ

    Args:
        race_id: レースID（YYYYMMDD_XX_RR形式）
    """
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return []

    # リアルタイムオッズを先に取得（jvd_o1テーブル）
    realtime_odds = get_realtime_odds(race_id)

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
        runners = [_to_runner_dict(row) for row in rows]

        # リアルタイムオッズがある場合は上書き
        if realtime_odds:
            for runner in runners:
                horse_number = runner.get("horse_number")
                if horse_number and horse_number in realtime_odds:
                    rt_odds = realtime_odds[horse_number]
                    runner["odds"] = rt_odds.get("odds")
                    runner["popularity"] = rt_odds.get("popularity")

        return runners


def get_realtime_odds(race_id: str) -> dict[int, dict] | None:
    """jvd_o1テーブルからリアルタイムオッズ（発売中オッズ）を取得.

    JRA-VANのjvd_o1テーブルには発売中（レース開始前）のオッズが格納されています。
    レース終了後の確定オッズはjvd_seテーブルに格納されます。

    Args:
        race_id: レースID（YYYYMMDD_XX_RR形式）
            例: "20260105_09_01" = 2026年1月5日 阪神 1R

    Returns:
        馬番をキー、オッズと人気を値とする辞書。
        例: {1: {"odds": 3.5, "popularity": 1}, 2: {"odds": 5.8, "popularity": 2}}
        テーブルが存在しない、またはデータがない場合はNone。

    Note:
        - jvd_o1テーブルのodds_tanshoカラムは全馬のオッズが連結された文字列:
          馬番(2桁) + オッズ(4桁, 10で割る) + 人気(2桁) = 8桁/馬
          例: "01055709" = 馬番1, オッズ55.7倍, 人気9位
        - オッズが10倍で格納されているのはJRA-VANの仕様
        - jvd_o1テーブルが存在しない環境ではNoneを返す
    """
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return None

    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT odds_tansho
                FROM jvd_o1
                WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
                  AND keibajo_code = %s AND race_bango = %s
            """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
            row = cur.fetchone()

            if not row or not row[0]:
                return None

            odds_str = row[0].strip()
            if not odds_str:
                return None

            # odds_tansho文字列を解析: 8桁/馬（馬番2 + オッズ4 + 人気2）
            result = {}
            for i in range(0, len(odds_str), 8):
                if i + 8 > len(odds_str):
                    break
                chunk = odds_str[i:i+8]
                if chunk.strip() == "" or len(chunk) < 8:
                    continue

                try:
                    horse_number = int(chunk[0:2])
                    odds_raw = int(chunk[2:6])
                    popularity_raw = int(chunk[6:8])

                    # オッズは10倍で格納されている（JRA-VAN仕様）
                    odds = odds_raw / 10.0 if odds_raw > 0 else None
                    popularity = popularity_raw if popularity_raw > 0 else None

                    if horse_number > 0:
                        result[horse_number] = {"odds": odds, "popularity": popularity}
                except (ValueError, IndexError):
                    continue

            return result if result else None
    except (EnvironmentError, OSError, Exception) as e:
        # DB接続エラー（テーブル不在含む）はNoneを返す
        # Note: pg8000のDatabaseErrorはExceptionを直接継承しているため、
        # Exception も含めてキャッチする必要がある
        logger.debug(f"Failed to get realtime odds: {e}")
        return None


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


def get_race_dates(from_date: str | None = None, to_date: str | None = None) -> list[str]:
    """開催日一覧を取得.

    Args:
        from_date: 開始日（YYYYMMDD形式、省略時は制限なし）
        to_date: 終了日（YYYYMMDD形式、省略時は制限なし）

    Returns:
        開催日のリスト（YYYYMMDD形式、降順）
    """
    with get_db() as conn:
        cur = conn.cursor()

        # 基本クエリ
        query = """
            SELECT DISTINCT kaisai_nen || kaisai_tsukihi as race_date
            FROM jvd_ra
            WHERE 1=1
        """
        params: list[str] = []

        if from_date:
            query += " AND kaisai_nen || kaisai_tsukihi >= %s"
            params.append(from_date)

        if to_date:
            query += " AND kaisai_nen || kaisai_tsukihi <= %s"
            params.append(to_date)

        query += " ORDER BY race_date DESC"

        cur.execute(query, params)
        rows = cur.fetchall()
        return [row[0] for row in rows]


def _build_race_name_from_codes(shubetsu_code: str, joken_code: str) -> str:
    """競走種別コードと条件コードからレース名を生成する.

    Args:
        shubetsu_code: 競走種別コード（11=2歳, 12=3歳, 13=3歳以上, 14=4歳以上）
        joken_code: 競走条件コード（701=新馬, 703=未勝利, 005=1勝クラス, etc）

    Returns:
        生成されたレース名（例: "3歳未勝利"）
    """
    # モジュール定数を使用（表示用の値を取得）
    shubetsu = AGE_CONDITION_MAP.get((shubetsu_code or "").strip(), "")
    class_info = RACE_CLASS_MAP.get((joken_code or "").strip(), {})
    joken = class_info.get("display", "") if class_info else ""

    if shubetsu and joken:
        return f"{shubetsu}{joken}"
    elif joken:
        return joken
    elif shubetsu:
        return shubetsu
    else:
        return ""


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
    is_obstacle = track_code.startswith("3")  # 3x = 障害
    if track_code.startswith("1"):
        track_type = "芝"
    elif track_code.startswith("2"):
        track_type = "ダート"
    elif is_obstacle:
        track_type = "障害"
    else:
        track_type = ""

    # 馬場状態コードの解釈（芝/ダートで分岐）
    if track_code.startswith("1"):
        baba_cd = row.get("babajotai_code_shiba", "") or ""
    else:
        baba_cd = row.get("babajotai_code_dirt", "") or ""
    baba_map = {"1": "良", "2": "稍重", "3": "重", "4": "不良"}
    track_condition = baba_map.get(baba_cd, "")

    # 競走種別コード（年齢条件）の解釈 - モジュール定数を使用
    shubetsu_code = (row.get("kyoso_shubetsu_code", "") or "").strip()
    age_condition = AGE_CONDITION_MAP.get(shubetsu_code, "")

    # 競走条件コード（クラス）の解釈 - モジュール定数を使用
    joken_code = (row.get("kyoso_joken_code", "") or "").strip()
    class_info = RACE_CLASS_MAP.get(joken_code, {})
    grade_class = class_info.get("api", "") if class_info else ""

    # グレードコードの解釈（重賞・リステッドはgrade_classを上書き）- モジュール定数を使用
    grade_cd = row.get("grade_code", "") or ""
    if grade_cd in GRADE_CODE_MAP:
        grade_class = GRADE_CODE_MAP[grade_cd]

    # レース名の組み立て
    race_name = (row.get("kyosomei_hondai", "") or "").strip()
    subtitle = (row.get("kyosomei_fukudai", "") or "").strip()

    # 本題が空の場合は種別・条件コードから生成
    if not race_name:
        race_name = _build_race_name_from_codes(shubetsu_code, joken_code)

    full_race_name = f"{race_name} {subtitle}".strip() if subtitle else race_name

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

    # 回次・日目（JRA出馬表URL生成用）
    kaisai_kai = (row.get("kaisai_kai", "") or "").strip()
    kaisai_nichime = (row.get("kaisai_nichime", "") or "").strip()

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
        # 条件フィールド
        "grade": grade_class,             # 互換性維持用のグレード（従来フィールド）
        "grade_class": grade_class,       # クラス（新馬、未勝利、1勝、G3など）
        "age_condition": age_condition,   # 年齢条件（3歳、4歳以上など）
        "is_obstacle": is_obstacle,       # 障害レース
        # JRA出馬表URL生成用
        "kaisai_kai": kaisai_kai,         # 回次（01, 02など）
        "kaisai_nichime": kaisai_nichime, # 日目（01, 02など）
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


def get_runners_with_running_style(race_id: str) -> list[dict]:
    """出走馬の脚質情報を含む一覧を取得.

    jvd_se.kyakushitsu_hantei と jvd_um.kyakushitsu_keiko を結合して取得。

    Args:
        race_id: レースID（YYYYMMDD_XX_RR形式）

    Returns:
        出走馬の脚質情報リスト
    """
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return []

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                se.umaban,
                se.bamei,
                se.kyakushitsu_hantei,
                um.kyakushitsu_keiko
            FROM jvd_se se
            LEFT JOIN jvd_um um ON se.ketto_toroku_bango = um.ketto_toroku_bango
            WHERE se.kaisai_nen = %s AND se.kaisai_tsukihi = %s
              AND se.keibajo_code = %s AND se.race_bango = %s
            ORDER BY se.umaban::integer
        """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
        rows = _fetch_all_as_dicts(cur)

        results = []
        for row in rows:
            try:
                horse_number = int(row.get("umaban", 0) or 0)
            except (ValueError, TypeError):
                horse_number = 0

            # 脚質判定コードをマッピング
            style_code = (row.get("kyakushitsu_hantei") or "").strip()
            running_style = RUNNING_STYLE_MAP.get(style_code, "不明")

            # 馬マスタの脚質傾向（1:逃げ 2:先行 3:差し 4:追込 5:自在）
            tendency_code = (row.get("kyakushitsu_keiko") or "").strip()
            running_style_tendency = RUNNING_STYLE_MAP.get(tendency_code, "不明")

            results.append({
                "horse_number": horse_number,
                "horse_name": (row.get("bamei") or "").strip(),
                "running_style": running_style,
                "running_style_code": style_code,
                "running_style_tendency": running_style_tendency,
            })

        return results


def calculate_jra_checksum(base_value: int, kaisai_nichime: int, race_number: int) -> int | None:
    """JRA出馬表URLのチェックサムを計算する.

    計算式:
    - 1R = (base_value + (日目-1) × 48) mod 256
    - 2R-9R = (1R + 181 × (レース番号-1)) mod 256
    - 10R = (9R + 245) mod 256
    - 11R, 12R = (前レース + 181) mod 256

    Args:
        base_value: その競馬場・回次の1日目1Rのbase値
        kaisai_nichime: 日目（1-12）
        race_number: レース番号（1-12）

    Returns:
        チェックサム値（0-255）、不正な入力の場合はNone
    """
    # 入力値のバリデーション
    if not (1 <= kaisai_nichime <= 12):
        return None
    if not (1 <= race_number <= 12):
        return None

    # 1R のチェックサム
    checksum_1r = (base_value + (kaisai_nichime - 1) * 48) % 256

    if race_number == 1:
        return checksum_1r

    # 2R-9R
    if 2 <= race_number <= 9:
        return (checksum_1r + 181 * (race_number - 1)) % 256

    # 10R = 9R + 245
    checksum_9r = (checksum_1r + 181 * 8) % 256
    if race_number == 10:
        return (checksum_9r + 245) % 256

    # 11R, 12R
    checksum_10r = (checksum_9r + 245) % 256
    if race_number == 11:
        return (checksum_10r + 181) % 256

    checksum_11r = (checksum_10r + 181) % 256
    if race_number == 12:
        return (checksum_11r + 181) % 256

    # ここには到達しないはず（バリデーションで弾かれる）
    return None


def get_jra_checksum(venue_code: str, kaisai_kai: str, kaisai_nichime: int, race_number: int) -> int | None:
    """JRA出馬表URLのチェックサムを取得する.

    Args:
        venue_code: 競馬場コード（01-10）
        kaisai_kai: 回次（01-05）
        kaisai_nichime: 日目（1-12）
        race_number: レース番号（1-12）

    Returns:
        チェックサム値（0-255）、データがない場合はNone
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT base_value
            FROM jra_url_checksums
            WHERE venue_code = %s AND kaisai_kai = %s
        """, (venue_code, kaisai_kai))
        row = cur.fetchone()

        if row is None:
            return None

        base_value = row[0]
        return calculate_jra_checksum(base_value, kaisai_nichime, race_number)


def save_jra_checksum(venue_code: str, kaisai_kai: str, base_value: int) -> bool:
    """JRA出馬表URLのbase_valueを保存する.

    Args:
        venue_code: 競馬場コード（01-10）
        kaisai_kai: 回次（01-05）
        base_value: 1日目1Rのbase値

    Returns:
        成功時True
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO jra_url_checksums (venue_code, kaisai_kai, base_value, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (venue_code, kaisai_kai) DO UPDATE
            SET base_value = EXCLUDED.base_value,
                updated_at = CURRENT_TIMESTAMP
        """, (venue_code, kaisai_kai, base_value))
        conn.commit()
        return True


def get_past_race_statistics(
    track_code: str,
    distance: int,
    grade_code: str | None = None,
    limit_races: int = 100
) -> dict | None:
    """過去の同コース・同距離のレース統計を取得.

    Args:
        track_code: トラックコード（"1": 芝コース, "2": ダートコース, "3": 障害コース。内部的には track_code LIKE '<code>%' でフィルタ）
        distance: 距離（メートル）
        grade_code: グレードコード（省略可）
        limit_races: 集計対象レース数

    Returns:
        人気別勝率・複勝率の統計
        {
            "total_races": int,
            "popularity_stats": [
                {
                    "popularity": int,
                    "total_runs": int,
                    "wins": int,
                    "places": int,
                    "win_rate": float,
                    "place_rate": float
                }
            ],
            "avg_win_payout": float | None,
            "avg_place_payout": float | None,
            "conditions": {
                "track_code": str,
                "distance": int,
                "grade_code": str | None
            }
        }
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()

            # CTEを使用してtarget_racesを一度だけ計算
            # これにより、人気別統計と配当統計で同じサブクエリが重複実行されることを防ぐ
            cte_query = """
                WITH target_races AS (
                    SELECT
                        ra.kaisai_nen,
                        ra.kaisai_tsukihi,
                        ra.keibajo_code,
                        ra.race_bango
                    FROM jvd_ra ra
                    WHERE ra.track_code LIKE %s
                      AND ra.kyori = %s
            """
            params = [f"{track_code}%", distance]

            if grade_code is not None:
                cte_query += " AND ra.grade_code = %s"
                params.append(grade_code)

            cte_query += """
                    ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC
                    LIMIT %s
                )
            """
            params.append(limit_races)

            # レース数を取得
            count_query = cte_query + """
                SELECT COUNT(*) FROM target_races
            """
            cur.execute(count_query, params)
            count_result = cur.fetchone()
            
            if not count_result or count_result[0] == 0:
                return None
            
            total_races = count_result[0]

            # 人気別統計を集計（kakutei_chakujun: 確定着順）
            stats_query = cte_query + """
                SELECT
                    se.tansho_ninkijun AS popularity,
                    COUNT(*) AS total_runs,
                    SUM(CASE WHEN se.kakutei_chakujun = '1' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN se.kakutei_chakujun IN ('1', '2', '3') THEN 1 ELSE 0 END) AS places
                FROM jvd_se se
                WHERE (se.kaisai_nen, se.kaisai_tsukihi, se.keibajo_code, se.race_bango) IN (
                    SELECT kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango
                    FROM target_races
                )
                AND se.tansho_ninkijun IS NOT NULL
                AND se.tansho_ninkijun != ''
                GROUP BY se.tansho_ninkijun
                ORDER BY se.tansho_ninkijun::integer
            """

            cur.execute(stats_query, params)
            popularity_rows = _fetch_all_as_dicts(cur)

            # 人気別統計を整形
            popularity_stats = []
            for row in popularity_rows:
                try:
                    pop = int(row["popularity"])
                    total = int(row["total_runs"])
                    wins = int(row["wins"])
                    places = int(row["places"])

                    popularity_stats.append({
                        "popularity": pop,
                        "total_runs": total,
                        "wins": wins,
                        "places": places,
                        "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
                        "place_rate": round(places / total * 100, 1) if total > 0 else 0.0,
                    })
                except (ValueError, TypeError, ZeroDivisionError):
                    continue

            # 平均配当を取得（jvd_hr テーブルから）
            payout_query = cte_query + """
                SELECT
                    AVG(NULLIF(hr.tansho_haraimodoshi_1, '')::numeric / 10) AS avg_win_payout,
                    AVG(
                        COALESCE(
                            NULLIF(hr.fukusho_haraimodoshi_1, '')::numeric / 10,
                            0
                        ) +
                        COALESCE(
                            NULLIF(hr.fukusho_haraimodoshi_2, '')::numeric / 10,
                            0
                        ) +
                        COALESCE(
                            NULLIF(hr.fukusho_haraimodoshi_3, '')::numeric / 10,
                            0
                        )
                    ) / NULLIF(
                        (CASE WHEN NULLIF(hr.fukusho_haraimodoshi_1, '') IS NOT NULL THEN 1 ELSE 0 END) +
                        (CASE WHEN NULLIF(hr.fukusho_haraimodoshi_2, '') IS NOT NULL THEN 1 ELSE 0 END) +
                        (CASE WHEN NULLIF(hr.fukusho_haraimodoshi_3, '') IS NOT NULL THEN 1 ELSE 0 END),
                        0
                    ) AS avg_place_payout
                FROM jvd_hr hr
                WHERE (hr.kaisai_nen, hr.kaisai_tsukihi, hr.keibajo_code, hr.race_bango) IN (
                    SELECT kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango
                    FROM target_races
                )
            """

            cur.execute(payout_query, params)
            payout_row = cur.fetchone()

            avg_win_payout = None
            avg_place_payout = None
            if payout_row:
                if payout_row[0] is not None:
                    avg_win_payout = round(float(payout_row[0]), 1)
                if payout_row[1] is not None:
                    avg_place_payout = round(float(payout_row[1]), 1)

            return {
                "total_races": total_races,
                "popularity_stats": popularity_stats,
                "avg_win_payout": avg_win_payout,
                "avg_place_payout": avg_place_payout,
                "conditions": {
                    "track_code": track_code,
                    "distance": distance,
                    "grade_code": grade_code,
                },
            }
    except Exception as e:
        logger.error(f"Failed to get past race statistics: {e}")
        return None


def get_jockey_course_stats(
    jockey_id: str,
    track_code: str,
    distance: int,
    keibajo_code: str | None = None,
    limit_races: int = 100,
) -> dict | None:
    """騎手の特定コースでの成績を取得.

    Args:
        jockey_id: 騎手コード
        track_code: トラックコード（1=芝, 2=ダート, 3=障害）
        distance: 距離（メートル）
        keibajo_code: 競馬場コード（Noneなら全競馬場）
        limit_races: 集計対象レース数上限

    Returns:
        {
            "jockey_id": str,
            "jockey_name": str,
            "total_rides": int,
            "wins": int,
            "places": int,
            "win_rate": float,
            "place_rate": float,
            "conditions": {...}
        }
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()

            # 騎手名を取得
            cur.execute("""
                SELECT kishumei
                FROM jvd_ks
                WHERE kishu_code = %s
                LIMIT 1
            """, (jockey_id,))
            jockey_row = cur.fetchone()
            jockey_name = jockey_row[0].strip() if jockey_row else "不明"

            # 成績集計クエリ
            stats_query = """
                SELECT
                    COUNT(*) AS total_rides,
                    SUM(CASE WHEN se.kakutei_chakujun = '1' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN se.kakutei_chakujun IN ('1', '2', '3') THEN 1 ELSE 0 END) AS places
                FROM jvd_se se
                INNER JOIN jvd_ra ra ON
                    se.kaisai_nen = ra.kaisai_nen AND
                    se.kaisai_tsukihi = ra.kaisai_tsukihi AND
                    se.keibajo_code = ra.keibajo_code AND
                    se.race_bango = ra.race_bango
                WHERE se.kishu_code = %s
                  AND ra.track_code LIKE %s
                  AND ra.kyori = %s
            """
            params = [jockey_id, f"{track_code}%", distance]

            if keibajo_code is not None:
                stats_query += " AND ra.keibajo_code = %s"
                params.append(keibajo_code)

            # 直近のデータに限定
            stats_query += """
                AND se.kakutei_chakujun IS NOT NULL
                AND se.kakutei_chakujun != ''
                ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC, ra.race_bango DESC
                LIMIT %s
            """
            params.append(limit_races)

            cur.execute(stats_query, params)
            row = cur.fetchone()

            if row is None or row[0] == 0:
                return None

            total_rides = int(row[0])
            wins = int(row[1])
            places = int(row[2])

            win_rate = round(wins / total_rides * 100, 1) if total_rides > 0 else 0.0
            place_rate = round(places / total_rides * 100, 1) if total_rides > 0 else 0.0

            return {
                "jockey_id": jockey_id,
                "jockey_name": jockey_name,
                "total_rides": total_rides,
                "wins": wins,
                "places": places,
                "win_rate": win_rate,
                "place_rate": place_rate,
                "conditions": {
                    "track_code": track_code,
                    "distance": distance,
                    "keibajo_code": keibajo_code,
                },
            }
    except Exception as e:
        logger.error(f"Failed to get jockey course stats: {e}")
        return None


def get_popularity_payout_stats(
    track_code: str,
    distance: int,
    popularity: int,
    limit_races: int = 100,
) -> dict | None:
    """特定人気の配当統計を取得.

    Args:
        track_code: トラックコード（1=芝, 2=ダート, 3=障害）
        distance: 距離（メートル）
        popularity: 人気順（1-18）
        limit_races: 集計対象レース数上限

    Returns:
        {
            "popularity": int,
            "total_races": int,
            "win_count": int,
            "avg_win_payout": float | None,
            "avg_place_payout": float | None,
            "estimated_roi_win": float,
            "estimated_roi_place": float,
        }
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()

            # 指定人気の馬の成績と配当を集計
            # jvd_hr テーブルから単勝・複勝配当を取得
            query = """
                WITH target_races AS (
                    SELECT
                        ra.kaisai_nen,
                        ra.kaisai_tsukihi,
                        ra.keibajo_code,
                        ra.race_bango
                    FROM jvd_ra ra
                    WHERE ra.track_code LIKE %s
                      AND ra.kyori = %s
                    ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC
                    LIMIT %s
                ),
                target_horses AS (
                    SELECT
                        se.kaisai_nen,
                        se.kaisai_tsukihi,
                        se.keibajo_code,
                        se.race_bango,
                        se.umaban,
                        se.kakutei_chakujun
                    FROM jvd_se se
                    INNER JOIN target_races tr ON
                        se.kaisai_nen = tr.kaisai_nen AND
                        se.kaisai_tsukihi = tr.kaisai_tsukihi AND
                        se.keibajo_code = tr.keibajo_code AND
                        se.race_bango = tr.race_bango
                    WHERE se.tansho_ninkijun = %s
                      AND se.kakutei_chakujun IS NOT NULL
                      AND se.kakutei_chakujun != ''
                )
                SELECT
                    COUNT(*) AS total_races,
                    SUM(CASE WHEN th.kakutei_chakujun = '1' THEN 1 ELSE 0 END) AS win_count,
                    SUM(CASE WHEN th.kakutei_chakujun IN ('1', '2', '3') THEN 1 ELSE 0 END) AS place_count,
                    AVG(CASE
                        WHEN th.kakutei_chakujun = '1' AND hr.tansho_haraimodoshi_1 IS NOT NULL
                        THEN NULLIF(hr.tansho_haraimodoshi_1, '')::numeric / 10
                        ELSE NULL
                    END) AS avg_win_payout,
                    -- 複勝配当は jvd_hr.fukusho_umaban_1〜3 に格納された馬番に対応する
                    -- fukusho_haraimodoshi_1〜3 を用いて算出する
                    AVG(
                        CASE
                            WHEN th.kakutei_chakujun IN ('1', '2', '3') THEN
                                CASE
                                    WHEN hr.fukusho_umaban_1 IS NOT NULL AND th.umaban = hr.fukusho_umaban_1 THEN
                                        NULLIF(hr.fukusho_haraimodoshi_1, '')::numeric / 10
                                    WHEN hr.fukusho_umaban_2 IS NOT NULL AND th.umaban = hr.fukusho_umaban_2 THEN
                                        NULLIF(hr.fukusho_haraimodoshi_2, '')::numeric / 10
                                    WHEN hr.fukusho_umaban_3 IS NOT NULL AND th.umaban = hr.fukusho_umaban_3 THEN
                                        NULLIF(hr.fukusho_haraimodoshi_3, '')::numeric / 10
                                    ELSE
                                        NULL
                                END
                            ELSE
                                NULL
                        END
                    ) AS avg_place_payout
                FROM target_horses th
                LEFT JOIN jvd_hr hr ON
                    th.kaisai_nen = hr.kaisai_nen AND
                    th.kaisai_tsukihi = hr.kaisai_tsukihi AND
                    th.keibajo_code = hr.keibajo_code AND
                    th.race_bango = hr.race_bango
            """
            params = [f"{track_code}%", distance, limit_races, str(popularity)]

            cur.execute(query, params)
            row = cur.fetchone()

            if row is None or row[0] == 0:
                return None

            total_races = int(row[0])
            win_count = int(row[1])
            place_count = int(row[2])
            avg_win_payout = float(row[3]) if row[3] is not None else None
            avg_place_payout = float(row[4]) if row[4] is not None else None

            # 回収率計算
            # 回収率(%) = 勝率(小数) × 平均配当(円)
            # ※100円あたりの払戻しを想定（例: 勝率0.3 × 平均配当300円 = 90%）
            win_rate_decimal = win_count / total_races if total_races > 0 else 0
            place_rate_decimal = place_count / total_races if total_races > 0 else 0
            if avg_win_payout is not None and win_count > 0:
                estimated_roi_win = round(win_rate_decimal * avg_win_payout, 1)
            else:
                estimated_roi_win = 0.0

            if avg_place_payout is not None and place_count > 0:
                estimated_roi_place = round(place_rate_decimal * avg_place_payout, 1)
            else:
                estimated_roi_place = 0.0

            return {
                "popularity": popularity,
                "total_races": total_races,
                "win_count": win_count,
                "avg_win_payout": round(avg_win_payout, 1) if avg_win_payout else None,
                "avg_place_payout": round(avg_place_payout, 1) if avg_place_payout else None,
                "estimated_roi_win": estimated_roi_win,
                "estimated_roi_place": estimated_roi_place,
            }
    except Exception as e:
        logger.error(f"Failed to get popularity payout stats: {e}")
        return None


# 所属コード → 名前のマッピング
AFFILIATION_CODE_MAP = {
    "1": "美浦",
    "2": "栗東",
}


def get_jockey_info(jockey_id: str) -> dict | None:
    """騎手基本情報を取得.

    Args:
        jockey_id: 騎手コード

    Returns:
        {
            "jockey_id": str,
            "jockey_name": str,
            "jockey_name_kana": str | None,
            "birth_date": str | None,  # YYYY-MM-DD形式
            "affiliation": str | None,  # 美浦/栗東
            "license_year": int | None,
        }
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    kishu_code,
                    kishumei,
                    kishumei_hankaku_kana,
                    seinengappi,
                    tozai_shozoku_code,
                    menkyo_kofu_nengappi
                FROM jvd_ks
                WHERE kishu_code = %s
                LIMIT 1
            """, (jockey_id,))
            row = cur.fetchone()

            if row is None:
                return None

            kishu_code = row[0]
            kishumei = (row[1] or "").strip()
            kishumei_kana = (row[2] or "").strip() or None
            seinengappi = (row[3] or "").strip()
            shozoku_code = (row[4] or "").strip()
            menkyo_nengappi = (row[5] or "").strip()

            # 生年月日をYYYY-MM-DD形式に変換
            birth_date = None
            if seinengappi and len(seinengappi) == 8:
                birth_date = f"{seinengappi[:4]}-{seinengappi[4:6]}-{seinengappi[6:8]}"

            # 所属コードを名前に変換
            affiliation = AFFILIATION_CODE_MAP.get(shozoku_code)

            # 免許年を取得
            license_year = None
            if menkyo_nengappi and len(menkyo_nengappi) >= 4:
                try:
                    license_year = int(menkyo_nengappi[:4])
                except ValueError:
                    # 免許年が数値に変換できない場合は不正データとして無視し、None のままとする
                    logger.debug(
                        "Failed to parse license year from menkyo_nengappi: %s",
                        menkyo_nengappi,
                    )

            return {
                "jockey_id": kishu_code,
                "jockey_name": kishumei,
                "jockey_name_kana": kishumei_kana,
                "birth_date": birth_date,
                "affiliation": affiliation,
                "license_year": license_year,
            }
    except Exception as e:
        logger.error(f"Failed to get jockey info: {e}")
        return None


def get_jockey_stats(
    jockey_id: str,
    year: int | None = None,
    period: str = "recent",  # recent/ytd/all
) -> dict | None:
    """騎手の成績統計を取得.

    Args:
        jockey_id: 騎手コード
        year: 年（指定時はその年の成績）
        period: 期間（recent=直近1年, ytd=今年初から, all=通算）

    Returns:
        {
            "jockey_id": str,
            "jockey_name": str,
            "total_rides": int,
            "wins": int,
            "second_places": int,
            "third_places": int,
            "win_rate": float,
            "place_rate": float,
            "period": str,
            "year": int | None,
        }
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()

            # 騎手名を取得
            cur.execute("""
                SELECT kishumei
                FROM jvd_ks
                WHERE kishu_code = %s
                LIMIT 1
            """, (jockey_id,))
            jockey_row = cur.fetchone()
            jockey_name = jockey_row[0].strip() if jockey_row else "不明"

            # 成績集計クエリの基本部分
            base_query = """
                SELECT
                    COUNT(*) AS total_rides,
                    SUM(CASE WHEN se.kakutei_chakujun = '1' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN se.kakutei_chakujun = '2' THEN 1 ELSE 0 END) AS second_places,
                    SUM(CASE WHEN se.kakutei_chakujun = '3' THEN 1 ELSE 0 END) AS third_places
                FROM jvd_se se
                WHERE se.kishu_code = %s
                  AND se.kakutei_chakujun IS NOT NULL
                  AND se.kakutei_chakujun != ''
                  AND se.kakutei_chakujun ~ '^[0-9]+$'
            """
            params: list = [jockey_id]

            # 期間条件を追加
            if year:
                base_query += " AND se.kaisai_nen = %s"
                params.append(str(year))
            elif period == "ytd":
                # 今年初から
                current_year = datetime.now().year
                base_query += " AND se.kaisai_nen = %s"
                params.append(str(current_year))
            elif period == "recent":
                # 直近1年（デフォルト）
                # timedeltaを使用して閏年(2/29)でのエラーを回避
                from datetime import timedelta
                one_year_ago = datetime.now() - timedelta(days=365)
                base_query += " AND (se.kaisai_nen || se.kaisai_tsukihi) >= %s"
                params.append(one_year_ago.strftime("%Y%m%d"))

            cur.execute(base_query, params)
            row = cur.fetchone()

            if row is None or row[0] == 0:
                return None

            total_rides = int(row[0])
            wins = int(row[1])
            second_places = int(row[2])
            third_places = int(row[3])
            places = wins + second_places + third_places

            win_rate = round(wins / total_rides * 100, 1) if total_rides > 0 else 0.0
            place_rate = round(places / total_rides * 100, 1) if total_rides > 0 else 0.0

            return {
                "jockey_id": jockey_id,
                "jockey_name": jockey_name,
                "total_rides": total_rides,
                "wins": wins,
                "second_places": second_places,
                "third_places": third_places,
                "win_rate": win_rate,
                "place_rate": place_rate,
                "period": period if not year else "year",
                "year": year,
            }
    except Exception as e:
        logger.error(f"Failed to get jockey stats: {e}")
        return None


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
