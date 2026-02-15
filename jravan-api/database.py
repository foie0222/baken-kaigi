"""PC-KEIBA Database (PostgreSQL) データアクセス層.

PC-KEIBA Database から直接レース・出走馬・血統情報を取得する。
pg8000 (pure Python PostgreSQL driver) を使用。
"""
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from pathlib import Path
from dotenv import load_dotenv
import pg8000

# .env ファイルから環境変数を読み込み（このファイルと同じディレクトリ）
load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

# PC-KEIBA Database 接続設定
DB_CONFIG = {
    "host": os.environ["PCKEIBA_HOST"],
    "port": int(os.environ["PCKEIBA_PORT"]),
    "database": os.environ["PCKEIBA_DATABASE"],
    "user": os.environ["PCKEIBA_USER"],
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
    # 障害レース
    # 障害の競走種別コードは21〜29まで存在するが、
    # 年齢条件を持つものとして21（3歳以上）, 22（4歳以上）のみを扱う。
    # 23〜29は現行データでは使用されておらず、あえてマッピングしない。
    "21": "3歳以上",
    "22": "4歳以上",
}

# 障害レースの競走種別コード（track_code未設定時のフォールバック判定用）
# 21〜29はすべて「障害レース」として扱うが、AGE_CONDITION_MAPで年齢条件が
# 定義されているのは21, 22のみである点に注意。
OBSTACLE_SHUBETSU_CODES = frozenset({"21", "22", "23", "24", "25", "26", "27", "28", "29"})

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
    password = os.environ["PCKEIBA_PASSWORD"]

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
              AND keibajo_code BETWEEN '01' AND '10'
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

        return runners


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
              AND keibajo_code BETWEEN '01' AND '10'
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
            WHERE keibajo_code BETWEEN '01' AND '10'
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

    # 競走種別コード（年齢条件・障害判定に使用）
    shubetsu_code = (row.get("kyoso_shubetsu_code", "") or "").strip()
    age_condition = AGE_CONDITION_MAP.get(shubetsu_code, "")

    # トラックコードの解釈
    track_code = row.get("track_code", "") or ""
    is_obstacle = track_code.startswith("3")  # 3x = 障害

    # track_codeが未設定の場合、競走種別コードからフォールバック判定
    if not is_obstacle and shubetsu_code in OBSTACLE_SHUBETSU_CODES:
        is_obstacle = True

    # track_codeもshubetsu_codeも障害を示さない場合、レース名からフォールバック判定
    # track_codeが芝(1x)・ダート(2x)の場合は平地確定なのでスキップ
    if not is_obstacle and not track_code.startswith(("1", "2")):
        race_name = (row.get("kyosomei_hondai", "") or "") + (row.get("kyosomei_fukudai", "") or "")
        if "ジャンプ" in race_name or "障害" in race_name:
            is_obstacle = True

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


def _parse_happyo_timestamp(kaisai_nen: str, happyo: str) -> str:
    """happyo_tsukihi_jifun を ISO8601 タイムスタンプに変換する.

    Args:
        kaisai_nen: 開催年（例: "2026"）
        happyo: 発表月日時分（例: "02081627" → 2月8日16:27）

    Returns:
        ISO8601 形式のタイムスタンプ文字列
    """
    if not happyo or happyo == "00000000" or len(happyo) < 8:
        return datetime.now().isoformat()

    try:
        month = int(happyo[0:2])
        day = int(happyo[2:4])
        hour = int(happyo[4:6])
        minute = int(happyo[6:8])
        year = int(kaisai_nen)
        return datetime(year, month, day, hour, minute).isoformat()
    except (ValueError, IndexError):
        return datetime.now().isoformat()


def _parse_fukusho_odds(odds_fukusho: str) -> list[dict]:
    """odds_fukusho 文字列を解析する.

    JRA-VAN jvd_o1 の odds_fukusho カラムは12文字/馬で連結:
    馬番(2桁) + 最低オッズ(4桁, ÷10) + 最高オッズ(4桁, ÷10) + 人気(2桁)

    取消馬は "XX**********" (馬番2桁 + アスタリスク10個) となる。

    Args:
        odds_fukusho: 複勝オッズ連結文字列

    Returns:
        複勝オッズリスト
    """
    if not odds_fukusho:
        return []

    odds_fukusho = odds_fukusho.strip()
    result = []
    for i in range(0, len(odds_fukusho), 12):
        chunk = odds_fukusho[i:i + 12]
        if len(chunk) < 12:
            break
        if "***" in chunk:
            continue
        try:
            horse_number = int(chunk[0:2])
            odds_min = int(chunk[2:6]) / 10.0
            odds_max = int(chunk[6:10]) / 10.0
            popularity = int(chunk[10:12])

            if horse_number > 0 and odds_min > 0:
                result.append({
                    "horse_number": horse_number,
                    "odds_min": odds_min,
                    "odds_max": odds_max,
                    "popularity": popularity,
                })
        except (ValueError, IndexError):
            continue

    return result


def _parse_combination_odds_2h(odds_str: str | None) -> dict[str, float]:
    """2頭組合せオッズ文字列を解析する.

    jvd_o2(馬連)/o3(ワイド)/o4(馬単) 用パーサー。
    13文字/組: kumiban(4桁) + odds(6桁, ÷10) + ninkijun(3桁)

    取消馬は "XXXX******NNN" のようにオッズ部分がアスタリスクとなる。

    Args:
        odds_str: オッズ連結文字列

    Returns:
        組番をキー、オッズを値とする辞書。例: {"1-2": 64.8}
    """
    if not odds_str:
        return {}

    odds_str = odds_str.strip()
    result: dict[str, float] = {}
    for i in range(0, len(odds_str), 13):
        chunk = odds_str[i:i + 13]
        if len(chunk) < 13:
            break
        if "***" in chunk:
            continue
        try:
            h1 = int(chunk[0:2])
            h2 = int(chunk[2:4])
            odds_raw = int(chunk[4:10])
            odds = odds_raw / 10.0

            if h1 > 0 and h2 > 0 and odds > 0:
                result[f"{h1}-{h2}"] = odds
        except (ValueError, IndexError):
            continue

    return result


def _parse_combination_odds_3h(odds_str: str | None) -> dict[str, float]:
    """3頭組合せオッズ文字列を解析する.

    jvd_o5(三連複)/o6(三連単) 用パーサー。
    15文字/組: kumiban(6桁) + odds(6桁, ÷10) + ninkijun(3桁)

    取消馬はオッズ部分がアスタリスクとなる。

    Args:
        odds_str: オッズ連結文字列

    Returns:
        組番をキー、オッズを値とする辞書。例: {"1-2-3": 341.9}
    """
    if not odds_str:
        return {}

    odds_str = odds_str.strip()
    result: dict[str, float] = {}
    for i in range(0, len(odds_str), 15):
        chunk = odds_str[i:i + 15]
        if len(chunk) < 15:
            break
        if "***" in chunk:
            continue
        try:
            h1 = int(chunk[0:2])
            h2 = int(chunk[2:4])
            h3 = int(chunk[4:6])
            odds_raw = int(chunk[6:12])
            odds = odds_raw / 10.0

            if h1 > 0 and h2 > 0 and h3 > 0 and odds > 0:
                result[f"{h1}-{h2}-{h3}"] = odds
        except (ValueError, IndexError):
            continue

    return result


def _parse_tansho_odds(
    odds_tansho: str, horse_names: dict[int, str],
) -> list[dict]:
    """odds_tansho 文字列を解析する.

    JRA-VAN の odds_tansho カラムは8文字/馬で連結:
    馬番(2桁) + オッズ(4桁, ÷10) + 人気(2桁)

    取消馬は "XX******" となる。

    Args:
        odds_tansho: 単勝オッズ連結文字列
        horse_names: 馬番→馬名の辞書

    Returns:
        オッズリスト
    """
    if not odds_tansho:
        return []

    odds_tansho = odds_tansho.strip()
    result = []
    for i in range(0, len(odds_tansho), 8):
        if i + 8 > len(odds_tansho):
            break
        chunk = odds_tansho[i:i + 8]
        if chunk.strip() == "" or "***" in chunk:
            continue
        try:
            horse_number = int(chunk[0:2])
            odds_raw = int(chunk[2:6])
            popularity = int(chunk[6:8])
            odds = odds_raw / 10.0 if odds_raw > 0 else None

            if horse_number > 0 and odds is not None:
                result.append({
                    "horse_number": horse_number,
                    "horse_name": horse_names.get(horse_number, ""),
                    "odds": odds,
                    "popularity": popularity if popularity > 0 else None,
                })
        except (ValueError, IndexError):
            continue

    return result


def _get_horse_names(
    kaisai_nen: str, kaisai_tsukihi: str,
    keibajo_code: str, race_bango: str,
) -> dict[int, str]:
    """出走馬名を jvd_se から取得する."""
    horse_names: dict[int, str] = {}
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT umaban, bamei
                FROM jvd_se
                WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
                  AND keibajo_code = %s AND race_bango = %s
                ORDER BY umaban::integer
            """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
            for row in _fetch_all_as_dicts(cur):
                try:
                    num = int(row.get("umaban", 0) or 0)
                    name = (row.get("bamei", "") or "").strip()
                    if num > 0:
                        horse_names[num] = name
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        logger.debug(f"Failed to get horse names: {e}")
    return horse_names


def get_odds_history(race_id: str) -> dict | None:
    """レースのオッズ履歴を取得する.

    データ取得の優先順位:
    1. apd_sokuho_o1: 時系列オッズ（複数タイムスタンプ）
    2. jvd_o1: 最新スナップショット（1行のみ）
    3. jvd_se: 確定オッズ（レース後）

    Args:
        race_id: レースID（YYYYMMDD_XX_RR形式）

    Returns:
        オッズ履歴データ。データがない場合はNone。
        形式: {"race_id": str, "odds_history": [{"timestamp": str, "odds": [...]}]}
    """
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return None

    horse_names = _get_horse_names(
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango,
    )

    # 1. apd_sokuho_o1 から時系列データを取得
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT odds_tansho, happyo_tsukihi_jifun
                FROM apd_sokuho_o1
                WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
                  AND keibajo_code = %s AND race_bango = %s
                ORDER BY happyo_tsukihi_jifun
            """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
            sokuho_rows = cur.fetchall()
    except Exception as e:
        logger.debug(f"Failed to get apd_sokuho_o1 data: {e}")
        sokuho_rows = []

    if sokuho_rows:
        odds_history = []
        for row in sokuho_rows:
            odds_tansho = (row[0] or "").strip()
            happyo = (row[1] or "").strip() if row[1] else ""
            timestamp = _parse_happyo_timestamp(kaisai_nen, happyo)
            odds_list = _parse_tansho_odds(odds_tansho, horse_names)
            if odds_list:
                odds_history.append({"timestamp": timestamp, "odds": odds_list})

        if odds_history:
            return {"race_id": race_id, "odds_history": odds_history}

    # 2. jvd_o1 から最新スナップショットを取得
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT odds_tansho, happyo_tsukihi_jifun
                FROM jvd_o1
                WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
                  AND keibajo_code = %s AND race_bango = %s
            """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
            row = cur.fetchone()
    except Exception as e:
        logger.debug(f"Failed to get jvd_o1 data: {e}")
        row = None

    if row and row[0]:
        odds_tansho = (row[0] or "").strip()
        happyo = (row[1] or "").strip() if row[1] else ""
        timestamp = _parse_happyo_timestamp(kaisai_nen, happyo)
        odds_list = _parse_tansho_odds(odds_tansho, horse_names)
        if odds_list:
            return {
                "race_id": race_id,
                "odds_history": [{"timestamp": timestamp, "odds": odds_list}],
            }

    # 3. jvd_se の確定オッズにフォールバック
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT umaban, tansho_odds, tansho_ninkijun
                FROM jvd_se
                WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
                  AND keibajo_code = %s AND race_bango = %s
                ORDER BY umaban::integer
            """, (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango))
            rows = _fetch_all_as_dicts(cur)

            odds_list = []
            for r in rows:
                try:
                    horse_number = int(r.get("umaban", 0) or 0)
                    odds_str = r.get("tansho_odds", "") or ""
                    odds = float(odds_str) / 10 if str(odds_str).isdigit() else None
                    pop_str = r.get("tansho_ninkijun", "") or ""
                    popularity = int(pop_str) if str(pop_str).isdigit() else None

                    if horse_number > 0 and odds is not None:
                        odds_list.append({
                            "horse_number": horse_number,
                            "horse_name": horse_names.get(horse_number, ""),
                            "odds": odds,
                            "popularity": popularity,
                        })
                except (ValueError, TypeError):
                    continue

            if not odds_list:
                return None

            return {
                "race_id": race_id,
                "odds_history": [{
                    "timestamp": datetime.now().isoformat(),
                    "odds": odds_list,
                }],
            }
    except Exception as e:
        logger.debug(f"Failed to get confirmed odds: {e}")
        return None


def get_all_odds(race_id: str) -> dict | None:
    """全券種のオッズを一括取得する.

    jvd_o1〜o6 から単勝・複勝・馬連・ワイド・馬単・三連複・三連単を取得。

    Args:
        race_id: レースID（YYYYMMDD_XX_RR形式）

    Returns:
        全券種オッズを含む辞書。全テーブルが空の場合はNone。
    """
    try:
        kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango = _parse_race_id(race_id)
    except ValueError:
        return None

    race_params = (kaisai_nen, kaisai_tsukihi, keibajo_code, race_bango)
    where_clause = """WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
                  AND keibajo_code = %s AND race_bango = %s"""

    try:
        with get_db() as conn:
            cur = conn.cursor()

            # jvd_o1: 単勝 + 複勝
            cur.execute(f"""
                SELECT odds_tansho, odds_fukusho FROM jvd_o1 {where_clause}
            """, race_params)
            o1_row = cur.fetchone()

            # jvd_o2: 馬連
            cur.execute(f"""
                SELECT odds_umaren FROM jvd_o2 {where_clause}
            """, race_params)
            o2_row = cur.fetchone()

            # jvd_o3: ワイド
            cur.execute(f"""
                SELECT odds_wide FROM jvd_o3 {where_clause}
            """, race_params)
            o3_row = cur.fetchone()

            # jvd_o4: 馬単
            cur.execute(f"""
                SELECT odds_umatan FROM jvd_o4 {where_clause}
            """, race_params)
            o4_row = cur.fetchone()

            # jvd_o5: 三連複
            cur.execute(f"""
                SELECT odds_sanrenpuku FROM jvd_o5 {where_clause}
            """, race_params)
            o5_row = cur.fetchone()

            # jvd_o6: 三連単
            cur.execute(f"""
                SELECT odds_sanrentan FROM jvd_o6 {where_clause}
            """, race_params)
            o6_row = cur.fetchone()

        # 単勝
        win: dict[str, float] = {}
        if o1_row and o1_row[0]:
            for entry in _parse_tansho_odds(o1_row[0], {}):
                win[str(entry["horse_number"])] = entry["odds"]

        # 複勝
        place: dict[str, dict[str, float]] = {}
        if o1_row and o1_row[1]:
            for entry in _parse_fukusho_odds(o1_row[1]):
                place[str(entry["horse_number"])] = {
                    "min": entry["odds_min"],
                    "max": entry["odds_max"],
                }

        # 馬連
        quinella = _parse_combination_odds_2h(o2_row[0] if o2_row else None)
        # ワイド
        quinella_place = _parse_combination_odds_2h(o3_row[0] if o3_row else None)
        # 馬単
        exacta = _parse_combination_odds_2h(o4_row[0] if o4_row else None)
        # 三連複
        trio = _parse_combination_odds_3h(o5_row[0] if o5_row else None)
        # 三連単
        trifecta = _parse_combination_odds_3h(o6_row[0] if o6_row else None)

        # 全て空ならNone
        if not any([win, place, quinella, quinella_place, exacta, trio, trifecta]):
            return None

        return {
            "win": win,
            "place": place,
            "quinella": quinella,
            "quinella_place": quinella_place,
            "exacta": exacta,
            "trio": trio,
            "trifecta": trifecta,
        }

    except Exception as e:
        logger.debug(f"Failed to get all odds: {e}")
        return None


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
            # kyakushitsu_hantei はレース後に確定するため、未開催レースでは空。
            # その場合、馬マスタの kyakushitsu_keiko（脚質傾向）にフォールバックする。
            style_code = (row.get("kyakushitsu_hantei") or "").strip()
            if not style_code:
                style_code = (row.get("kyakushitsu_keiko") or "").strip()
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


CHECKSUM_STALENESS_DAYS = 7


def get_jra_checksum(venue_code: str, kaisai_kai: str, kaisai_nichime: int, race_number: int) -> int | None:
    """JRA出馬表URLのチェックサムを取得する.

    updated_at が CHECKSUM_STALENESS_DAYS 日以上前の場合は
    古いデータとみなし None を返す（不正リンク防止）。

    Args:
        venue_code: 競馬場コード（01-10）
        kaisai_kai: 回次（01-05）
        kaisai_nichime: 日目（1-12）
        race_number: レース番号（1-12）

    Returns:
        チェックサム値（0-255）、データがない場合またはデータが古い場合はNone
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT base_value, updated_at
            FROM jra_url_checksums
            WHERE venue_code = %s AND kaisai_kai = %s
        """, (venue_code, kaisai_kai))
        row = cur.fetchone()

        if row is None:
            logger.warning(
                f"base_value not found for venue_code={venue_code}, kaisai_kai={kaisai_kai}, "
                f"kaisai_nichime={kaisai_nichime}, race_number={race_number}. "
                "Register via POST /jra-checksum endpoint."
            )
            return None

        base_value = row[0]
        updated_at = row[1]

        if updated_at is not None:
            jst = timezone(timedelta(hours=9))
            now = datetime.now(jst)
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=jst)
            age = now - updated_at
            if age > timedelta(days=CHECKSUM_STALENESS_DAYS):
                logger.warning(
                    f"Stale checksum data for venue_code={venue_code}, kaisai_kai={kaisai_kai}: "
                    f"updated_at={updated_at}, age={age.days} days. Returning None."
                )
                return None

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

            # 基本的な条件でレースを絞り込む
            base_query = """
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
                base_query += " AND ra.grade_code = %s"
                params.append(grade_code)

            base_query += " ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC LIMIT %s"
            params.append(limit_races)

            cur.execute(base_query, params)
            races = cur.fetchall()

            if not races:
                return None

            total_races = len(races)

            # 人気別統計を集計（kakutei_chakujun: 確定着順）
            stats_query = """
                SELECT
                    se.tansho_ninkijun AS popularity,
                    COUNT(*) AS total_runs,
                    SUM(CASE WHEN se.kakutei_chakujun = '1' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN se.kakutei_chakujun IN ('1', '2', '3') THEN 1 ELSE 0 END) AS places
                FROM jvd_se se
                WHERE (se.kaisai_nen, se.kaisai_tsukihi, se.keibajo_code, se.race_bango) IN (
                    SELECT ra.kaisai_nen, ra.kaisai_tsukihi, ra.keibajo_code, ra.race_bango
                    FROM jvd_ra ra
                    WHERE ra.track_code LIKE %s
                      AND ra.kyori = %s
            """
            stats_params = [f"{track_code}%", distance]

            if grade_code is not None:
                stats_query += " AND ra.grade_code = %s"
                stats_params.append(grade_code)

            stats_query += """
                    ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC
                    LIMIT %s
                )
                AND se.tansho_ninkijun IS NOT NULL
                AND se.tansho_ninkijun != ''
                GROUP BY se.tansho_ninkijun
                ORDER BY se.tansho_ninkijun::integer
            """
            stats_params.append(limit_races)

            cur.execute(stats_query, stats_params)
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
            # 複勝配当は各レースの1着〜3着それぞれの配当を個別に平均化
            payout_query = """
                WITH target_races AS (
                    SELECT ra.kaisai_nen, ra.kaisai_tsukihi, ra.keibajo_code, ra.race_bango
                    FROM jvd_ra ra
                    WHERE ra.track_code LIKE %s
                      AND ra.kyori = %s
            """
            payout_params = [f"{track_code}%", distance]

            if grade_code is not None:
                payout_query += " AND ra.grade_code = %s"
                payout_params.append(grade_code)

            payout_query += """
                    ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC
                    LIMIT %s
                ),
                all_place_payouts AS (
                    SELECT NULLIF(hr.fukusho_haraimodoshi_1, '')::numeric / 10 AS payout
                    FROM jvd_hr hr
                    INNER JOIN target_races tr ON
                        hr.kaisai_nen = tr.kaisai_nen AND
                        hr.kaisai_tsukihi = tr.kaisai_tsukihi AND
                        hr.keibajo_code = tr.keibajo_code AND
                        hr.race_bango = tr.race_bango
                    WHERE NULLIF(hr.fukusho_haraimodoshi_1, '') IS NOT NULL
                    UNION ALL
                    SELECT NULLIF(hr.fukusho_haraimodoshi_2, '')::numeric / 10 AS payout
                    FROM jvd_hr hr
                    INNER JOIN target_races tr ON
                        hr.kaisai_nen = tr.kaisai_nen AND
                        hr.kaisai_tsukihi = tr.kaisai_tsukihi AND
                        hr.keibajo_code = tr.keibajo_code AND
                        hr.race_bango = tr.race_bango
                    WHERE NULLIF(hr.fukusho_haraimodoshi_2, '') IS NOT NULL
                    UNION ALL
                    SELECT NULLIF(hr.fukusho_haraimodoshi_3, '')::numeric / 10 AS payout
                    FROM jvd_hr hr
                    INNER JOIN target_races tr ON
                        hr.kaisai_nen = tr.kaisai_nen AND
                        hr.kaisai_tsukihi = tr.kaisai_tsukihi AND
                        hr.keibajo_code = tr.keibajo_code AND
                        hr.race_bango = tr.race_bango
                    WHERE NULLIF(hr.fukusho_haraimodoshi_3, '') IS NOT NULL
                )
                SELECT
                    (SELECT AVG(NULLIF(hr.tansho_haraimodoshi_1, '')::numeric / 10)
                     FROM jvd_hr hr
                     INNER JOIN target_races tr ON
                         hr.kaisai_nen = tr.kaisai_nen AND
                         hr.kaisai_tsukihi = tr.kaisai_tsukihi AND
                         hr.keibajo_code = tr.keibajo_code AND
                         hr.race_bango = tr.race_bango) AS avg_win_payout,
                    (SELECT AVG(payout) FROM all_place_payouts) AS avg_place_payout
            """
            payout_params.append(limit_races)

            cur.execute(payout_query, payout_params)
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


def get_current_kaisai_info(target_date: str) -> list[dict]:
    """指定日の開催情報を取得する.

    Args:
        target_date: 日付（YYYYMMDD形式）

    Returns:
        開催情報のリスト
        [{"venue_code": "05", "kaisai_kai": "01", "kaisai_nichime": 3, "date": "20260207"}, ...]

    Raises:
        TypeError: target_dateが文字列でない場合
        ValueError: target_dateが不正な形式の場合
    """
    kaisai_nen, kaisai_tsukihi = _validate_date(target_date)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT
                keibajo_code,
                kaisai_kai,
                kaisai_nichime
            FROM jvd_ra
            WHERE kaisai_nen = %s AND kaisai_tsukihi = %s
            ORDER BY keibajo_code
        """, (kaisai_nen, kaisai_tsukihi))
        rows = _fetch_all_as_dicts(cur)

        results = []
        for row in rows:
            raw_nichime = row.get("kaisai_nichime")
            try:
                nichime = int(raw_nichime)
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid kaisai_nichime '%s' for date=%s, venue_code=%s. Skipping.",
                    raw_nichime, target_date, row.get("keibajo_code"),
                )
                continue
            if not 1 <= nichime <= 12:
                logger.warning(
                    "Out-of-range kaisai_nichime '%s' for date=%s, venue_code=%s. Skipping.",
                    raw_nichime, target_date, row.get("keibajo_code"),
                )
                continue
            results.append({
                "venue_code": row["keibajo_code"],
                "kaisai_kai": (row["kaisai_kai"] or "").strip(),
                "kaisai_nichime": nichime,
                "date": target_date,
            })
        return results


# 競馬場名 → コードの逆引きマッピング
VENUE_NAME_TO_CODE = {name: code for code, name in VENUE_CODE_MAP.items()}

# 馬場状態名 → コードの逆引きマッピング
TRACK_CONDITION_CODE_MAP = {"良": "1", "稍重": "2", "重": "3", "不良": "4"}

# 馬場状態コード → 名前の逆引きマッピング（TRACK_CONDITION_CODE_MAPの逆引き）
TRACK_CONDITION_NAME_MAP = {v: k for k, v in TRACK_CONDITION_CODE_MAP.items()}

# 枠順有利/不利判定の閾値: 全体平均勝率との差(%)
GATE_ADVANTAGE_THRESHOLD = 5.0

# 距離帯の分類定義
DISTANCE_RANGES = [
    ("短距離", 0, 1400),
    ("マイル", 1500, 1800),
    ("中距離", 1900, 2200),
    ("長距離", 2300, 99999),
]


def _classify_distance(distance: int) -> str:
    """距離を距離帯に分類する."""
    for label, low, high in DISTANCE_RANGES:
        if low <= distance <= high:
            return label
    return "その他"


def _classify_gate(wakuban: int) -> str:
    """枠番から内枠/中枠/外枠に分類する."""
    if wakuban <= 2:
        return "内枠"
    elif wakuban <= 6:
        return "中枠"
    else:
        return "外枠"


def get_horse_course_aptitude(horse_id: str) -> dict | None:
    """馬のコース適性を集計する.

    jvd_se（出走結果）とjvd_ra（レース情報）をJOINして各カテゴリ別の成績を集計。

    Args:
        horse_id: 血統登録番号（ketto_toroku_bango）

    Returns:
        コース適性データ。データがない場合はNone。
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()

            # 馬名を取得
            cur.execute("""
                SELECT bamei FROM jvd_um WHERE ketto_toroku_bango = %s
            """, (horse_id,))
            name_row = cur.fetchone()
            horse_name = name_row[0].strip() if name_row else None

            # 出走結果とレース情報をJOINして取得
            cur.execute("""
                SELECT
                    ra.keibajo_code,
                    ra.track_code,
                    ra.kyori,
                    ra.babajotai_code_shiba,
                    ra.babajotai_code_dirt,
                    se.wakuban,
                    se.kakutei_chakujun,
                    se.run_time
                FROM jvd_se se
                INNER JOIN jvd_ra ra ON
                    se.kaisai_nen = ra.kaisai_nen AND
                    se.kaisai_tsukihi = ra.kaisai_tsukihi AND
                    se.keibajo_code = ra.keibajo_code AND
                    se.race_bango = ra.race_bango
                WHERE se.ketto_toroku_bango = %s
                  AND se.kakutei_chakujun IS NOT NULL
                  AND se.kakutei_chakujun != ''
                  AND se.kakutei_chakujun ~ '^[0-9]+$'
                ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC
            """, (horse_id,))
            rows = _fetch_all_as_dicts(cur)

            if not rows:
                return None

            # 各カテゴリ別に集計
            venue_stats: dict[str, dict] = {}
            track_type_stats: dict[str, dict] = {}
            distance_stats: dict[str, dict] = {}
            condition_stats: dict[str, dict] = {}
            position_stats: dict[str, dict] = {}

            for row in rows:
                chakujun = int(row["kakutei_chakujun"])
                is_win = chakujun == 1
                is_place = chakujun <= 3

                # by_venue
                keibajo_code = (row.get("keibajo_code") or "").strip()
                venue_name = VENUE_CODE_MAP.get(keibajo_code, keibajo_code)
                if venue_name not in venue_stats:
                    venue_stats[venue_name] = {"starts": 0, "wins": 0, "places": 0}
                venue_stats[venue_name]["starts"] += 1
                if is_win:
                    venue_stats[venue_name]["wins"] += 1
                if is_place:
                    venue_stats[venue_name]["places"] += 1

                # by_track_type
                track_code = (row.get("track_code") or "").strip()
                if track_code.startswith("1"):
                    track_type = "芝"
                elif track_code.startswith("2"):
                    track_type = "ダート"
                else:
                    track_type = "その他"
                if track_type not in track_type_stats:
                    track_type_stats[track_type] = {"starts": 0, "wins": 0}
                track_type_stats[track_type]["starts"] += 1
                if is_win:
                    track_type_stats[track_type]["wins"] += 1

                # by_distance
                try:
                    distance = int(row.get("kyori", 0) or 0)
                except (ValueError, TypeError):
                    distance = 0
                distance_range = _classify_distance(distance)
                if distance_range not in distance_stats:
                    distance_stats[distance_range] = {"starts": 0, "wins": 0, "best_time": None}
                distance_stats[distance_range]["starts"] += 1
                if is_win:
                    distance_stats[distance_range]["wins"] += 1
                # best_time の更新
                run_time = (row.get("run_time") or "").strip()
                if run_time and run_time != "0":
                    current_best = distance_stats[distance_range]["best_time"]
                    if current_best is None or run_time < current_best:
                        distance_stats[distance_range]["best_time"] = run_time

                # by_track_condition
                if track_code.startswith("1"):
                    baba_cd = (row.get("babajotai_code_shiba") or "").strip()
                else:
                    baba_cd = (row.get("babajotai_code_dirt") or "").strip()
                condition = TRACK_CONDITION_NAME_MAP.get(baba_cd, "不明")
                if condition != "不明":
                    if condition not in condition_stats:
                        condition_stats[condition] = {"starts": 0, "wins": 0}
                    condition_stats[condition]["starts"] += 1
                    if is_win:
                        condition_stats[condition]["wins"] += 1

                # by_running_position (枠番)
                try:
                    wakuban = int(row.get("wakuban", 0) or 0)
                except (ValueError, TypeError):
                    wakuban = 0
                if wakuban >= 1:
                    position = _classify_gate(wakuban)
                    if position not in position_stats:
                        position_stats[position] = {"starts": 0, "wins": 0}
                    position_stats[position]["starts"] += 1
                    if is_win:
                        position_stats[position]["wins"] += 1

            # レスポンス構築
            def _rate(wins: int, starts: int) -> float:
                return round(wins / starts * 100, 1) if starts > 0 else 0.0

            by_venue = [
                {
                    "venue": v,
                    "starts": s["starts"],
                    "wins": s["wins"],
                    "places": s["places"],
                    "win_rate": _rate(s["wins"], s["starts"]),
                    "place_rate": _rate(s["places"], s["starts"]),
                }
                for v, s in venue_stats.items()
            ]

            by_track_type = [
                {
                    "track_type": t,
                    "starts": s["starts"],
                    "wins": s["wins"],
                    "win_rate": _rate(s["wins"], s["starts"]),
                }
                for t, s in track_type_stats.items()
            ]

            by_distance = [
                {
                    "distance_range": d,
                    "starts": s["starts"],
                    "wins": s["wins"],
                    "win_rate": _rate(s["wins"], s["starts"]),
                    "best_time": s["best_time"],
                }
                for d, s in distance_stats.items()
            ]

            by_track_condition = [
                {
                    "condition": c,
                    "starts": s["starts"],
                    "wins": s["wins"],
                    "win_rate": _rate(s["wins"], s["starts"]),
                }
                for c, s in condition_stats.items()
            ]

            by_running_position = [
                {
                    "position": p,
                    "starts": s["starts"],
                    "wins": s["wins"],
                    "win_rate": _rate(s["wins"], s["starts"]),
                }
                for p, s in position_stats.items()
            ]

            # aptitude_summary: 各カテゴリで最高勝率
            def _best_key(items: list[dict], key: str) -> str | None:
                if not items:
                    return None
                best = max(items, key=lambda x: x["win_rate"])
                return best[key] if best["win_rate"] > 0 else None

            aptitude_summary = {
                "best_venue": _best_key(by_venue, "venue"),
                "best_distance": _best_key(by_distance, "distance_range"),
                "preferred_condition": _best_key(by_track_condition, "condition"),
                "preferred_position": _best_key(by_running_position, "position"),
            }

            return {
                "horse_id": horse_id,
                "horse_name": horse_name,
                "by_venue": by_venue,
                "by_track_type": by_track_type,
                "by_distance": by_distance,
                "by_track_condition": by_track_condition,
                "by_running_position": by_running_position,
                "aptitude_summary": aptitude_summary,
            }
    except Exception as e:
        logger.error(f"Failed to get horse course aptitude: {e}")
        return None


def get_gate_position_stats(
    venue: str,
    track_type: str | None = None,
    distance: int | None = None,
    track_condition: str | None = None,
    limit: int = 200,
) -> dict | None:
    """枠順・馬番別の成績統計を取得する.

    Args:
        venue: 競馬場名（例: "東京", "阪神"）
        track_type: 芝/ダート（任意）
        distance: 距離（任意）
        track_condition: 馬場状態（良/稍重/重/不良）（任意）
        limit: 集計対象レース数上限（任意）

    Returns:
        枠順傾向データ。データがない場合はNone。
    """
    # 競馬場名 → コードに変換
    keibajo_code = VENUE_NAME_TO_CODE.get(venue)
    if keibajo_code is None:
        return None

    try:
        with get_db() as conn:
            cur = conn.cursor()

            # レース絞り込み条件を構築
            race_where = "ra.keibajo_code = %s"
            race_params: list = [keibajo_code]

            if track_type is not None:
                if track_type == "芝":
                    race_where += " AND ra.track_code LIKE '1%'"
                elif track_type == "ダート":
                    race_where += " AND ra.track_code LIKE '2%'"

            if distance is not None:
                race_where += " AND ra.kyori = %s"
                race_params.append(distance)

            if track_condition is not None:
                cond_code = TRACK_CONDITION_CODE_MAP.get(track_condition)
                if cond_code:
                    race_where += " AND (ra.babajotai_code_shiba = %s OR ra.babajotai_code_dirt = %s)"
                    race_params.append(cond_code)
                    race_params.append(cond_code)

            # 対象レースを取得
            race_query = f"""
                SELECT ra.kaisai_nen, ra.kaisai_tsukihi, ra.keibajo_code, ra.race_bango
                FROM jvd_ra ra
                WHERE {race_where}
                ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC
                LIMIT %s
            """
            race_params.append(limit)

            cur.execute(race_query, race_params)
            races = cur.fetchall()

            if not races:
                return None

            total_races = len(races)

            # 枠番・馬番別の成績を集計（LIMITはレース数制限なのでサブクエリを使う）
            se_params = list(race_params)  # race_paramsにはLIMIT値が含まれている

            stats_query = f"""
                SELECT
                    se.wakuban,
                    se.umaban,
                    se.kakutei_chakujun
                FROM jvd_se se
                INNER JOIN (
                    SELECT ra.kaisai_nen, ra.kaisai_tsukihi, ra.keibajo_code, ra.race_bango
                    FROM jvd_ra ra
                    WHERE {race_where}
                    ORDER BY ra.kaisai_nen DESC, ra.kaisai_tsukihi DESC
                    LIMIT %s
                ) ra ON
                    se.kaisai_nen = ra.kaisai_nen AND
                    se.kaisai_tsukihi = ra.kaisai_tsukihi AND
                    se.keibajo_code = ra.keibajo_code AND
                    se.race_bango = ra.race_bango
                WHERE se.kakutei_chakujun IS NOT NULL
                  AND se.kakutei_chakujun != ''
                  AND se.kakutei_chakujun ~ '^[0-9]+$'
            """

            cur.execute(stats_query, se_params)
            result_rows = _fetch_all_as_dicts(cur)

            if not result_rows:
                return None

            # 枠番別集計
            gate_stats: dict[int, dict] = {}
            # 馬番別集計
            horse_number_stats: dict[int, dict] = {}

            for row in result_rows:
                try:
                    wakuban = int(row.get("wakuban", 0) or 0)
                    umaban = int(row.get("umaban", 0) or 0)
                    chakujun = int(row["kakutei_chakujun"])
                except (ValueError, TypeError):
                    continue

                is_win = chakujun == 1
                is_place = chakujun <= 3

                # 枠番集計
                if 1 <= wakuban <= 8:
                    if wakuban not in gate_stats:
                        gate_stats[wakuban] = {
                            "starts": 0, "wins": 0, "places": 0, "finish_sum": 0,
                        }
                    gate_stats[wakuban]["starts"] += 1
                    if is_win:
                        gate_stats[wakuban]["wins"] += 1
                    if is_place:
                        gate_stats[wakuban]["places"] += 1
                    gate_stats[wakuban]["finish_sum"] += chakujun

                # 馬番集計
                if 1 <= umaban <= 18:
                    if umaban not in horse_number_stats:
                        horse_number_stats[umaban] = {"starts": 0, "wins": 0}
                    horse_number_stats[umaban]["starts"] += 1
                    if is_win:
                        horse_number_stats[umaban]["wins"] += 1

            def _rate(wins: int, starts: int) -> float:
                return round(wins / starts * 100, 1) if starts > 0 else 0.0

            # gate_range のマッピング
            gate_range_map = {
                1: "1-2枠", 2: "1-2枠",
                3: "3-4枠", 4: "3-4枠",
                5: "5-6枠", 6: "5-6枠",
                7: "7-8枠", 8: "7-8枠",
            }

            by_gate = []
            for gate in sorted(gate_stats.keys()):
                s = gate_stats[gate]
                by_gate.append({
                    "gate": gate,
                    "gate_range": gate_range_map.get(gate, f"{gate}枠"),
                    "starts": s["starts"],
                    "wins": s["wins"],
                    "places": s["places"],
                    "win_rate": _rate(s["wins"], s["starts"]),
                    "place_rate": _rate(s["places"], s["starts"]),
                    "avg_finish": round(s["finish_sum"] / s["starts"], 1) if s["starts"] > 0 else 0.0,
                })

            by_horse_number = []
            for num in sorted(horse_number_stats.keys()):
                s = horse_number_stats[num]
                by_horse_number.append({
                    "horse_number": num,
                    "starts": s["starts"],
                    "wins": s["wins"],
                    "win_rate": _rate(s["wins"], s["starts"]),
                })

            # analysis: 有利/不利な枠の分析
            total_wins = sum(s["wins"] for s in gate_stats.values())
            total_starts = sum(s["starts"] for s in gate_stats.values())
            avg_win_rate = (total_wins / total_starts * 100) if total_starts > 0 else 0.0

            favorable_gates = [
                g["gate"] for g in by_gate
                if g["win_rate"] >= avg_win_rate + GATE_ADVANTAGE_THRESHOLD
            ]
            unfavorable_gates = [
                g["gate"] for g in by_gate
                if g["win_rate"] <= avg_win_rate - GATE_ADVANTAGE_THRESHOLD
            ]

            # コメント生成
            comment_parts = []
            if favorable_gates:
                gates_str = "・".join(str(g) for g in favorable_gates)
                comment_parts.append(f"{gates_str}枠が有利")
            if unfavorable_gates:
                gates_str = "・".join(str(g) for g in unfavorable_gates)
                comment_parts.append(f"{gates_str}枠が不利")
            if not comment_parts:
                comment = "枠順による有利不利の差は小さい"
            else:
                comment = "、".join(comment_parts)

            return {
                "conditions": {
                    "venue": venue,
                    "track_type": track_type,
                    "distance": distance,
                    "track_condition": track_condition,
                },
                "total_races": total_races,
                "by_gate": by_gate,
                "by_horse_number": by_horse_number,
                "analysis": {
                    "favorable_gates": favorable_gates,
                    "unfavorable_gates": unfavorable_gates,
                    "comment": comment,
                },
            }
    except Exception as e:
        logger.error(f"Failed to get gate position stats: {e}")
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
