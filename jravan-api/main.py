"""JRA-VAN FastAPI サーバー.

SQLite から読み込んでレース情報を返す。
データは sync_jvlink.py で事前に同期しておく。
"""
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="JRA-VAN API",
    description="JV-Link データを提供する API（SQLite ベース）",
    version="2.0.0",
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """アプリケーション起動時に DB を初期化."""
    db.init_db()
    logger.info("Database initialized")


# ========================================
# レスポンスモデル
# ========================================


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス."""
    status: str
    database: str
    last_sync: str | None


class RaceResponse(BaseModel):
    """レース情報レスポンス."""
    race_id: str
    race_name: str
    race_number: int
    venue: str
    venue_name: str
    start_time: datetime
    betting_deadline: datetime
    distance: int
    track_type: str
    track_condition: str
    grade: str


class RunnerResponse(BaseModel):
    """出走馬情報レスポンス."""
    horse_number: int
    horse_name: str
    horse_id: str
    jockey_name: str
    jockey_id: str
    trainer_name: str
    weight: float
    odds: float | None
    popularity: int | None


class SyncStatusResponse(BaseModel):
    """同期状態レスポンス."""
    last_timestamp: str | None
    last_sync_at: str | None
    record_count: int


# ========================================
# エンドポイント
# ========================================


@app.get("/health", response_model=HealthResponse)
def health_check():
    """ヘルスチェック."""
    sync_status = db.get_sync_status()
    return HealthResponse(
        status="ok",
        database=str(db.DB_PATH),
        last_sync=sync_status.get("last_sync_at"),
    )


@app.get("/sync-status", response_model=SyncStatusResponse)
def get_sync_status():
    """同期状態を取得."""
    status = db.get_sync_status()
    return SyncStatusResponse(
        last_timestamp=status.get("last_timestamp"),
        last_sync_at=status.get("last_sync_at"),
        record_count=status.get("record_count", 0),
    )


@app.get("/races", response_model=list[RaceResponse])
def get_races(
    date: str = Query(..., description="日付（YYYYMMDD）"),
    venue: str | None = Query(None, description="開催場所コード"),
):
    """指定日のレース一覧を取得する."""
    races = db.get_races_by_date(date)

    if venue:
        races = [r for r in races if r["venue_code"] == venue]

    return [
        RaceResponse(
            race_id=r["race_id"],
            race_name=r["race_name"],
            race_number=r["race_number"],
            venue=r["venue_code"],
            venue_name=r["venue_name"],
            start_time=datetime.fromisoformat(r["start_time"]) if r["start_time"] else datetime.now(),
            betting_deadline=datetime.fromisoformat(r["start_time"]) if r["start_time"] else datetime.now(),
            distance=r["distance"] or 0,
            track_type=r["track_type"] or "",
            track_condition=r["track_condition"] or "",
            grade=r["grade"] or "",
        )
        for r in races
    ]


@app.get("/races/{race_id}", response_model=RaceResponse)
def get_race(race_id: str):
    """レース詳細を取得する."""
    race = db.get_race_by_id(race_id)

    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    return RaceResponse(
        race_id=race["race_id"],
        race_name=race["race_name"],
        race_number=race["race_number"],
        venue=race["venue_code"],
        venue_name=race["venue_name"],
        start_time=datetime.fromisoformat(race["start_time"]) if race["start_time"] else datetime.now(),
        betting_deadline=datetime.fromisoformat(race["start_time"]) if race["start_time"] else datetime.now(),
        distance=race["distance"] or 0,
        track_type=race["track_type"] or "",
        track_condition=race["track_condition"] or "",
        grade=race["grade"] or "",
    )


@app.get("/races/{race_id}/runners", response_model=list[RunnerResponse])
def get_runners(race_id: str):
    """出走馬情報を取得する."""
    runners = db.get_runners_by_race(race_id)

    return [
        RunnerResponse(
            horse_number=r["horse_number"],
            horse_name=r["horse_name"],
            horse_id=r["horse_id"] or "",
            jockey_name=r["jockey_name"] or "",
            jockey_id=r["jockey_id"] or "",
            trainer_name=r["trainer_name"] or "",
            weight=r["weight"] or 0.0,
            odds=r["odds"],
            popularity=r["popularity"],
        )
        for r in runners
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
