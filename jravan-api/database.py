"""SQLite データベース管理."""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "jvdata.db"


def get_connection() -> sqlite3.Connection:
    """DB 接続を取得."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """DB 接続のコンテキストマネージャー."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """DB を初期化（テーブル作成）."""
    with get_db() as conn:
        conn.executescript("""
            -- レーステーブル
            CREATE TABLE IF NOT EXISTS races (
                race_id TEXT PRIMARY KEY,
                race_date TEXT NOT NULL,
                race_name TEXT,
                race_number INTEGER,
                venue_code TEXT,
                venue_name TEXT,
                start_time TEXT,
                distance INTEGER,
                track_type TEXT,
                track_condition TEXT,
                grade TEXT,
                kai TEXT,
                nichiji TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- レース日付のインデックス
            CREATE INDEX IF NOT EXISTS idx_races_date ON races(race_date);

            -- 出走馬テーブル
            CREATE TABLE IF NOT EXISTS runners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id TEXT NOT NULL,
                horse_number INTEGER,
                horse_name TEXT,
                horse_id TEXT,
                jockey_name TEXT,
                jockey_id TEXT,
                trainer_name TEXT,
                weight REAL,
                odds REAL,
                popularity INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (race_id) REFERENCES races(race_id)
            );

            -- race_id のインデックス
            CREATE INDEX IF NOT EXISTS idx_runners_race_id ON runners(race_id);

            -- 同期状態テーブル
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_timestamp TEXT,
                last_sync_at TEXT,
                record_count INTEGER DEFAULT 0
            );

            -- 初期レコード
            INSERT OR IGNORE INTO sync_status (id, last_timestamp, last_sync_at, record_count)
            VALUES (1, '00000000000000', NULL, 0);
        """)
        logger.info(f"Database initialized at {DB_PATH}")


def get_races_by_date(date: str) -> list[dict]:
    """指定日のレース一覧を取得."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM races
            WHERE race_date = ?
            ORDER BY race_number
            """,
            (date,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_race_by_id(race_id: str) -> dict | None:
    """レース詳細を取得."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM races WHERE race_id = ?",
            (race_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_runners_by_race(race_id: str) -> list[dict]:
    """出走馬一覧を取得."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM runners
            WHERE race_id = ?
            ORDER BY horse_number
            """,
            (race_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_horse_count(race_id: str) -> int:
    """レースの出走馬数を取得."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM runners WHERE race_id = ?",
            (race_id,)
        )
        row = cursor.fetchone()
        return row["count"] if row else 0


def get_horse_counts_by_date(date: str) -> dict[str, int]:
    """指定日のレースごとの出走馬数を取得."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT r.race_id, COUNT(ru.id) as count
            FROM races r
            LEFT JOIN runners ru ON r.race_id = ru.race_id
            WHERE r.race_date = ?
            GROUP BY r.race_id
            """,
            (date,)
        )
        return {row["race_id"]: row["count"] for row in cursor.fetchall()}


def upsert_race(race: dict):
    """レースを追加/更新."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO races (
                race_id, race_date, race_name, race_number,
                venue_code, venue_name, start_time, distance,
                track_type, track_condition, grade, kai, nichiji, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(race_id) DO UPDATE SET
                race_name = excluded.race_name,
                start_time = excluded.start_time,
                distance = excluded.distance,
                track_type = excluded.track_type,
                track_condition = excluded.track_condition,
                grade = excluded.grade,
                updated_at = excluded.updated_at
            """,
            (
                race["race_id"],
                race["race_date"],
                race["race_name"],
                race["race_number"],
                race["venue_code"],
                race["venue_name"],
                race["start_time"],
                race["distance"],
                race["track_type"],
                race["track_condition"],
                race["grade"],
                race["kai"],
                race["nichiji"],
                datetime.now().isoformat(),
            )
        )


def upsert_runner(runner: dict):
    """出走馬を追加/更新."""
    with get_db() as conn:
        # 既存レコードを削除して挿入（シンプルな方法）
        conn.execute(
            """
            DELETE FROM runners
            WHERE race_id = ? AND horse_number = ?
            """,
            (runner["race_id"], runner["horse_number"])
        )
        conn.execute(
            """
            INSERT INTO runners (
                race_id, horse_number, horse_name, horse_id,
                jockey_name, jockey_id, trainer_name, weight,
                odds, popularity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                runner["race_id"],
                runner["horse_number"],
                runner["horse_name"],
                runner["horse_id"],
                runner["jockey_name"],
                runner["jockey_id"],
                runner["trainer_name"],
                runner["weight"],
                runner["odds"],
                runner["popularity"],
            )
        )


def update_runner_odds(race_id: str, horse_number: int, odds: float, popularity: int):
    """出走馬のオッズと人気を更新."""
    with get_db() as conn:
        conn.execute(
            """
            UPDATE runners
            SET odds = ?, popularity = ?
            WHERE race_id = ? AND horse_number = ?
            """,
            (odds, popularity, race_id, horse_number)
        )


def get_sync_status() -> dict:
    """同期状態を取得."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM sync_status WHERE id = 1")
        row = cursor.fetchone()
        return dict(row) if row else {}


def update_sync_status(last_timestamp: str, record_count: int):
    """同期状態を更新."""
    with get_db() as conn:
        conn.execute(
            """
            UPDATE sync_status
            SET last_timestamp = ?, last_sync_at = ?, record_count = ?
            WHERE id = 1
            """,
            (last_timestamp, datetime.now().isoformat(), record_count)
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print(f"Database created at {DB_PATH}")
