"""JRA-VAN FastAPI サーバー.

PC-KEIBA Database (PostgreSQL) からレース情報を提供する。
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
    description="PC-KEIBA Database からレースデータを提供する API",
    version="3.0.0",
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
    """アプリケーション起動時に DB 接続を確認."""
    if db.check_connection():
        logger.info("PC-KEIBA Database connected")
    else:
        logger.error("Failed to connect to PC-KEIBA Database")


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
    start_time: datetime | None
    betting_deadline: datetime | None
    distance: int
    track_type: str
    track_condition: str
    grade: str
    horse_count: int = 0
    # 条件フィールド
    grade_class: str = ""      # クラス（新馬、未勝利、1勝、G3など）
    age_condition: str = ""    # 年齢条件（3歳、4歳以上など）
    is_obstacle: bool = False  # 障害レース
    # JRA出馬表URL生成用
    kaisai_kai: str = ""       # 回次（01, 02など）
    kaisai_nichime: str = ""   # 日目（01, 02など）


class RunnerResponse(BaseModel):
    """出走馬情報レスポンス."""
    horse_number: int
    waku_ban: int
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


class PedigreeResponse(BaseModel):
    """血統情報レスポンス."""
    horse_id: str
    horse_name: str | None
    sire_name: str | None       # 父
    dam_name: str | None        # 母
    broodmare_sire: str | None  # 母父


class WeightResponse(BaseModel):
    """馬体重レスポンス."""
    weight: int                 # 馬体重(kg)
    weight_diff: int            # 前走比増減
    race_id: str | None = None
    race_date: str | None = None
    race_name: str | None = None


class RaceWeightResponse(BaseModel):
    """レースの馬体重レスポンス."""
    horse_number: int
    weight: int                 # 馬体重(kg)
    weight_diff: int            # 前走比増減


# ========================================
# エンドポイント
# ========================================


@app.get("/health", response_model=HealthResponse)
def health_check():
    """ヘルスチェック."""
    connected = db.check_connection()
    sync_status = db.get_sync_status() if connected else {}
    return HealthResponse(
        status="ok" if connected else "error",
        database="PC-KEIBA PostgreSQL",
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
    horse_counts = db.get_horse_counts_by_date(date)

    if venue:
        races = [r for r in races if r["venue_code"] == venue]

    result = []
    for r in races:
        start_time = None
        if r["start_time"]:
            try:
                start_time = datetime.fromisoformat(r["start_time"])
            except (ValueError, TypeError) as exc:
                # 不正な開始時刻は None として扱い、詳細をログに記録する
                logger.warning(
                    "Invalid start_time format for race_id=%s: %r (%s)",
                    r.get("race_id"),
                    r.get("start_time"),
                    exc,
                )

        result.append(RaceResponse(
            race_id=r["race_id"],
            race_name=r["race_name"],
            race_number=r["race_number"],
            venue=r["venue_code"],
            venue_name=r["venue_name"],
            start_time=start_time,
            betting_deadline=start_time,
            distance=r["distance"] or 0,
            track_type=r["track_type"] or "",
            track_condition=r["track_condition"] or "",
            grade=r["grade"] or "",
            horse_count=horse_counts.get(r["race_id"], 0),
            # 条件フィールド
            grade_class=r.get("grade_class") or "",
            age_condition=r.get("age_condition") or "",
            is_obstacle=r.get("is_obstacle", False),
            # JRA出馬表URL生成用
            kaisai_kai=r.get("kaisai_kai") or "",
            kaisai_nichime=r.get("kaisai_nichime") or "",
        ))

    return result


@app.get("/races/{race_id}", response_model=RaceResponse)
def get_race(race_id: str):
    """レース詳細を取得する."""
    race = db.get_race_by_id(race_id)

    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    horse_count = db.get_horse_count(race_id)

    start_time = None
    if race["start_time"]:
        try:
            start_time = datetime.fromisoformat(race["start_time"])
        except (ValueError, TypeError) as exc:
            # 不正な開始時刻は None として扱い、詳細をログに記録する
            logger.warning(
                "Invalid start_time format for race_id=%s: %r (%s)",
                race.get("race_id"),
                race.get("start_time"),
                exc,
            )

    return RaceResponse(
        race_id=race["race_id"],
        race_name=race["race_name"],
        race_number=race["race_number"],
        venue=race["venue_code"],
        venue_name=race["venue_name"],
        start_time=start_time,
        betting_deadline=start_time,
        distance=race["distance"] or 0,
        track_type=race["track_type"] or "",
        track_condition=race["track_condition"] or "",
        grade=race["grade"] or "",
        horse_count=horse_count,
        # 条件フィールド
        grade_class=race.get("grade_class") or "",
        age_condition=race.get("age_condition") or "",
        is_obstacle=race.get("is_obstacle", False),
        # JRA出馬表URL生成用
        kaisai_kai=race.get("kaisai_kai") or "",
        kaisai_nichime=race.get("kaisai_nichime") or "",
    )


@app.get("/races/{race_id}/runners", response_model=list[RunnerResponse])
def get_runners(race_id: str):
    """出走馬情報を取得する."""
    runners = db.get_runners_by_race(race_id)

    return [
        RunnerResponse(
            horse_number=r["horse_number"],
            waku_ban=r.get("waku_ban") or 0,
            horse_name=r["horse_name"],
            horse_id=r["horse_id"] or "",
            jockey_name=r["jockey_name"] or "",
            jockey_id=r["jockey_id"] or "",
            trainer_name=r["trainer_name"] or "",
            weight=r["weight"] or 0.0,
            odds=r.get("odds"),
            popularity=r.get("popularity"),
        )
        for r in runners
    ]


@app.get("/horses/{horse_id}/pedigree", response_model=PedigreeResponse)
def get_pedigree(horse_id: str):
    """馬の血統情報を取得する."""
    pedigree = db.get_horse_pedigree(horse_id)

    if not pedigree:
        raise HTTPException(status_code=404, detail="Horse not found")

    return PedigreeResponse(
        horse_id=pedigree["horse_id"],
        horse_name=pedigree.get("horse_name"),
        sire_name=pedigree.get("sire_name"),
        dam_name=pedigree.get("dam_name"),
        broodmare_sire=pedigree.get("broodmare_sire"),
    )


@app.get("/horses/{horse_id}/weights", response_model=list[WeightResponse])
def get_weight_history(
    horse_id: str,
    limit: int = Query(5, description="取得件数"),
):
    """馬の体重履歴を取得する."""
    weights = db.get_horse_weight_history(horse_id, limit)

    return [
        WeightResponse(
            weight=w["weight"],
            weight_diff=w["weight_diff"],
            race_id=w.get("race_id"),
            race_date=w.get("race_date"),
            race_name=w.get("race_name"),
        )
        for w in weights
    ]


@app.get("/races/{race_id}/weights", response_model=list[RaceWeightResponse])
def get_race_weights(race_id: str):
    """レースの馬体重情報を取得する."""
    weights = db.get_race_weights(race_id)

    return [
        RaceWeightResponse(
            horse_number=w["horse_number"],
            weight=w["weight"],
            weight_diff=w["weight_diff"],
        )
        for w in weights
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
