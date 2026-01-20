"""JRA-VAN FastAPI サーバー.

Lambda からの HTTP リクエストを受けて JV-Link 経由でデータを返す。
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from jvlink_client import JVLinkClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# グローバル JV-Link クライアント
jvlink: JVLinkClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理."""
    global jvlink
    jvlink = JVLinkClient()
    if not jvlink.init():
        logger.error("Failed to initialize JV-Link")
    yield
    if jvlink:
        jvlink.close()


app = FastAPI(
    title="JRA-VAN API",
    description="JV-Link 経由で JRA データを提供する API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 設定（VPC 内からのアクセス用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# レスポンスモデル
# ========================================


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス."""

    status: str
    jvlink_initialized: bool


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


class PerformanceResponse(BaseModel):
    """過去成績レスポンス."""

    race_date: datetime
    race_name: str
    venue: str
    finish_position: int
    distance: int
    track_condition: str
    time: str


class JockeyStatsResponse(BaseModel):
    """騎手成績レスポンス."""

    jockey_id: str
    jockey_name: str
    course: str
    total_races: int
    wins: int
    win_rate: float
    place_rate: float


# ========================================
# エンドポイント
# ========================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェック."""
    return HealthResponse(
        status="ok",
        jvlink_initialized=jvlink is not None and jvlink._initialized,
    )


@app.get("/races", response_model=list[RaceResponse])
async def get_races(
    date: str = Query(..., description="日付（YYYYMMDD）"),
    venue: str | None = Query(None, description="開催場所コード"),
):
    """指定日のレース一覧を取得する."""
    if not jvlink or not jvlink._initialized:
        raise HTTPException(status_code=503, detail="JV-Link is not initialized")

    try:
        races = jvlink.get_race_list(date)

        # 開催場所でフィルタ
        if venue:
            races = [r for r in races if r.venue == venue]

        return [
            RaceResponse(
                race_id=r.race_id,
                race_name=r.race_name,
                race_number=r.race_number,
                venue=r.venue,
                venue_name=r.venue_name,
                start_time=r.start_time,
                betting_deadline=r.start_time,  # 仮: 発走時刻と同じ
                distance=r.distance,
                track_type=r.track_type,
                track_condition=r.track_condition,
                grade=r.grade,
            )
            for r in races
        ]
    except Exception as e:
        logger.error(f"Failed to get races: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/races/{race_id}", response_model=RaceResponse)
async def get_race(race_id: str):
    """レース詳細を取得する."""
    if not jvlink or not jvlink._initialized:
        raise HTTPException(status_code=503, detail="JV-Link is not initialized")

    try:
        # 日付を抽出してレース一覧を取得
        date = race_id[:8]
        races = jvlink.get_race_list(date)

        for r in races:
            if r.race_id == race_id:
                return RaceResponse(
                    race_id=r.race_id,
                    race_name=r.race_name,
                    race_number=r.race_number,
                    venue=r.venue,
                    venue_name=r.venue_name,
                    start_time=r.start_time,
                    betting_deadline=r.start_time,
                    distance=r.distance,
                    track_type=r.track_type,
                    track_condition=r.track_condition,
                    grade=r.grade,
                )

        raise HTTPException(status_code=404, detail="Race not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get race: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/races/{race_id}/runners", response_model=list[RunnerResponse])
async def get_runners(race_id: str):
    """出走馬情報を取得する."""
    if not jvlink or not jvlink._initialized:
        raise HTTPException(status_code=503, detail="JV-Link is not initialized")

    try:
        runners = jvlink.get_runners(race_id)

        return [
            RunnerResponse(
                horse_number=r.horse_number,
                horse_name=r.horse_name,
                horse_id=r.horse_id,
                jockey_name=r.jockey_name,
                jockey_id=r.jockey_id,
                trainer_name=r.trainer_name,
                weight=r.weight,
                odds=r.odds,
                popularity=r.popularity,
            )
            for r in runners
        ]
    except Exception as e:
        logger.error(f"Failed to get runners: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/horses/{horse_id}/performances", response_model=list[PerformanceResponse])
async def get_performances(horse_id: str):
    """馬の過去成績を取得する."""
    if not jvlink or not jvlink._initialized:
        raise HTTPException(status_code=503, detail="JV-Link is not initialized")

    # TODO: JV-Link から過去成績を取得する実装
    # 現在は空リストを返す
    return []


@app.get("/jockeys/{jockey_id}/stats", response_model=JockeyStatsResponse | None)
async def get_jockey_stats(
    jockey_id: str,
    course: str = Query(..., description="コース名"),
):
    """騎手のコース成績を取得する."""
    if not jvlink or not jvlink._initialized:
        raise HTTPException(status_code=503, detail="JV-Link is not initialized")

    # TODO: JV-Link から騎手成績を取得する実装
    raise HTTPException(status_code=404, detail="Jockey stats not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
