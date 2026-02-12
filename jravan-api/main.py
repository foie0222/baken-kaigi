"""JRA-VAN FastAPI サーバー.

PC-KEIBA Database (PostgreSQL) からレース情報を提供する。
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db
from jra_checksum_scraper import scrape_jra_checksums

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


class RunningStyleResponse(BaseModel):
    """脚質情報レスポンス."""
    horse_number: int
    horse_name: str
    running_style: str          # 逃げ/先行/差し/追込/自在/不明
    running_style_code: str     # 元のコード
    running_style_tendency: str # 馬マスタの脚質傾向


class OddsEntry(BaseModel):
    """個別オッズレスポンス."""
    horse_number: int
    horse_name: str
    odds: float | None
    popularity: int | None


class OddsTimestamp(BaseModel):
    """タイムスタンプ付きオッズスナップショット."""
    timestamp: str
    odds: list[OddsEntry]


class OddsHistoryResponse(BaseModel):
    """オッズ履歴レスポンス."""
    race_id: str
    odds_history: list[OddsTimestamp]


class JraChecksumResponse(BaseModel):
    """JRAチェックサムレスポンス."""
    checksum: int | None


class JraChecksumSaveRequest(BaseModel):
    """JRAチェックサム保存リクエスト."""
    venue_code: str             # 競馬場コード (01-10)
    kaisai_kai: str             # 回次 (01-05)
    base_value: int             # 1日目1Rのbase値


class VenueAptitude(BaseModel):
    """競馬場別適性."""
    venue: str
    starts: int
    wins: int
    places: int
    win_rate: float
    place_rate: float


class TrackTypeAptitude(BaseModel):
    """トラック種別適性."""
    track_type: str
    starts: int
    wins: int
    win_rate: float


class DistanceAptitude(BaseModel):
    """距離帯別適性."""
    distance_range: str
    starts: int
    wins: int
    win_rate: float
    best_time: str | None


class TrackConditionAptitude(BaseModel):
    """馬場状態別適性."""
    condition: str
    starts: int
    wins: int
    win_rate: float


class RunningPositionAptitude(BaseModel):
    """枠位置別適性."""
    position: str
    starts: int
    wins: int
    win_rate: float


class AptitudeSummary(BaseModel):
    """適性サマリー."""
    best_venue: str | None
    best_distance: str | None
    preferred_condition: str | None
    preferred_position: str | None


class CourseAptitudeResponse(BaseModel):
    """コース適性レスポンス."""
    horse_id: str
    horse_name: str | None
    by_venue: list[VenueAptitude]
    by_track_type: list[TrackTypeAptitude]
    by_distance: list[DistanceAptitude]
    by_track_condition: list[TrackConditionAptitude]
    by_running_position: list[RunningPositionAptitude]
    aptitude_summary: AptitudeSummary


class GateStatEntry(BaseModel):
    """枠番別統計エントリ."""
    gate: int
    gate_range: str
    starts: int
    wins: int
    places: int
    win_rate: float
    place_rate: float
    avg_finish: float


class HorseNumberStatEntry(BaseModel):
    """馬番別統計エントリ."""
    horse_number: int
    starts: int
    wins: int
    win_rate: float


class GateConditions(BaseModel):
    """枠順統計の条件."""
    venue: str
    track_type: str | None
    distance: int | None
    track_condition: str | None


class GateAnalysis(BaseModel):
    """枠順分析."""
    favorable_gates: list[int]
    unfavorable_gates: list[int]
    comment: str


class GatePositionResponse(BaseModel):
    """枠順傾向レスポンス."""
    conditions: GateConditions
    total_races: int
    by_gate: list[GateStatEntry]
    by_horse_number: list[HorseNumberStatEntry]
    analysis: GateAnalysis


class PopularityStatResponse(BaseModel):
    """人気別統計レスポンス."""
    popularity: int
    total_runs: int
    wins: int
    places: int
    win_rate: float
    place_rate: float


class PastStatsResponse(BaseModel):
    """過去統計レスポンス."""
    total_races: int
    popularity_stats: list[PopularityStatResponse]
    avg_win_payout: float | None
    avg_place_payout: float | None
    conditions: dict


class JockeyCourseStatsResponse(BaseModel):
    """騎手コース成績レスポンス."""
    jockey_id: str
    jockey_name: str
    total_rides: int
    wins: int
    places: int
    win_rate: float
    place_rate: float
    conditions: dict


class PopularityPayoutResponse(BaseModel):
    """人気別配当統計レスポンス."""
    popularity: int
    total_races: int
    win_count: int
    avg_win_payout: float | None
    avg_place_payout: float | None
    estimated_roi_win: float
    estimated_roi_place: float


class JockeyInfoResponse(BaseModel):
    """騎手基本情報レスポンス."""
    jockey_id: str
    jockey_name: str
    jockey_name_kana: str | None = None
    birth_date: str | None = None  # YYYY-MM-DD形式
    affiliation: str | None = None  # 美浦/栗東
    license_year: int | None = None


class JockeyStatsResponse(BaseModel):
    """騎手成績統計レスポンス."""
    jockey_id: str
    jockey_name: str
    total_rides: int
    wins: int
    second_places: int
    third_places: int
    win_rate: float
    place_rate: float
    period: str  # recent/ytd/all/year
    year: int | None = None


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


@app.get("/race-dates", response_model=list[str])
def get_race_dates(
    from_date: str | None = Query(None, description="開始日（YYYYMMDD）"),
    to_date: str | None = Query(None, description="終了日（YYYYMMDD）"),
):
    """開催日一覧を取得する."""
    return db.get_race_dates(from_date, to_date)


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


@app.get("/horses/{horse_id}/course-aptitude", response_model=CourseAptitudeResponse)
def get_course_aptitude(horse_id: str):
    """馬のコース適性を取得する."""
    try:
        data = db.get_horse_course_aptitude(horse_id)

        if not data:
            raise HTTPException(
                status_code=404,
                detail="コース適性データが見つかりませんでした"
            )

        return CourseAptitudeResponse(**data)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get course aptitude")
        raise HTTPException(
            status_code=500,
            detail="コース適性データの取得に失敗しました"
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


@app.get("/races/{race_id}/running-styles", response_model=list[RunningStyleResponse])
def get_running_styles(race_id: str):
    """出走馬の脚質情報を取得する."""
    runners = db.get_runners_with_running_style(race_id)

    return [
        RunningStyleResponse(
            horse_number=r["horse_number"],
            horse_name=r["horse_name"],
            running_style=r["running_style"],
            running_style_code=r["running_style_code"],
            running_style_tendency=r["running_style_tendency"],
        )
        for r in runners
    ]


@app.get("/races/{race_id}/odds-history", response_model=OddsHistoryResponse)
def get_odds_history(race_id: str):
    """レースのオッズ履歴を取得する."""
    data = db.get_odds_history(race_id)
    if data is None:
        raise HTTPException(status_code=404, detail="オッズデータが見つかりません")

    return OddsHistoryResponse(
        race_id=data["race_id"],
        odds_history=[
            OddsTimestamp(
                timestamp=entry["timestamp"],
                odds=[
                    OddsEntry(
                        horse_number=o["horse_number"],
                        horse_name=o["horse_name"],
                        odds=o["odds"],
                        popularity=o.get("popularity"),
                    )
                    for o in entry["odds"]
                ],
            )
            for entry in data["odds_history"]
        ],
    )


@app.get("/jra-checksum", response_model=JraChecksumResponse)
def get_jra_checksum(
    venue_code: str = Query(..., description="競馬場コード（01-10）"),
    kaisai_kai: str = Query(..., description="回次（01-05）"),
    kaisai_nichime: int = Query(..., ge=1, le=12, description="日目（1-12）"),
    race_number: int = Query(..., ge=1, le=12, description="レース番号（1-12）"),
):
    """JRA出馬表URLのチェックサムを取得する."""
    # venue_code のバリデーション（01-10の2桁数字）
    if not venue_code.isdigit() or len(venue_code) != 2:
        raise HTTPException(
            status_code=400,
            detail="venue_code は 01〜10 の2桁数値文字列で指定してください。",
        )
    venue_code_int = int(venue_code)
    if venue_code_int < 1 or venue_code_int > 10:
        raise HTTPException(
            status_code=400,
            detail="venue_code は 01〜10 の範囲で指定してください。",
        )

    # kaisai_kai のバリデーション（01-05の2桁数字）
    if not kaisai_kai.isdigit() or len(kaisai_kai) != 2:
        raise HTTPException(
            status_code=400,
            detail="kaisai_kai は 01〜05 の2桁数値文字列で指定してください。",
        )
    kaisai_kai_int = int(kaisai_kai)
    if kaisai_kai_int < 1 or kaisai_kai_int > 5:
        raise HTTPException(
            status_code=400,
            detail="kaisai_kai は 01〜05 の範囲で指定してください。",
        )

    try:
        checksum = db.get_jra_checksum(venue_code, kaisai_kai, kaisai_nichime, race_number)
    except Exception:
        logger.exception("Failed to get JRA checksum from database")
        raise HTTPException(
            status_code=500,
            detail="データベースから JRA チェックサムを取得できませんでした。",
        )
    return JraChecksumResponse(checksum=checksum)


@app.post("/jra-checksum")
def save_jra_checksum(request: JraChecksumSaveRequest):
    """JRA出馬表URLのbase_valueを保存する（管理用）."""
    db.save_jra_checksum(
        request.venue_code,
        request.kaisai_kai,
        request.base_value,
    )
    return {"status": "ok"}


@app.post("/jra-checksum/auto-update")
def auto_update_jra_checksums(
    target_date: str | None = Query(None, description="対象日付（YYYYMMDD）。省略時は当日"),
):
    """JRAサイトから全会場のbase_valueを自動取得して更新する."""
    if target_date is None:
        jst = timezone(timedelta(hours=9))
        target_date = datetime.now(jst).strftime("%Y%m%d")

    # target_date の形式バリデーション（YYYYMMDD）
    try:
        db._validate_date(target_date)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=400,
            detail="target_date は YYYYMMDD 形式の8桁数値文字列で指定してください。",
        ) from e

    try:
        results = scrape_jra_checksums(target_date)
        saved_count = sum(1 for r in results if r["status"] == "saved")
        return {
            "status": "ok",
            "target_date": target_date,
            "total_venues": len(results),
            "saved_count": saved_count,
            "details": results,
        }
    except Exception as e:
        logger.exception("Failed to auto-update JRA checksums")
        raise HTTPException(
            status_code=500,
            detail=f"チェックサム自動更新に失敗しました: {str(e)}",
        )


@app.get("/statistics/gate-position", response_model=GatePositionResponse)
def get_gate_position_stats(
    venue: str = Query(..., description="競馬場名（例: 東京、阪神）"),
    track_type: Literal["芝", "ダート"] | None = Query(None, description="芝/ダート"),
    distance: int | None = Query(None, description="距離（メートル）"),
    track_condition: Literal["良", "稍重", "重", "不良"] | None = Query(None, description="馬場状態（良/稍重/重/不良）"),
    limit: int = Query(default=200, ge=1, le=1000, description="集計対象レース数上限"),
):
    """枠順・馬番別の成績統計を取得する."""
    try:
        data = db.get_gate_position_stats(
            venue=venue,
            track_type=track_type,
            distance=distance,
            track_condition=track_condition,
            limit=limit,
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail="枠順統計データが見つかりませんでした"
            )

        return GatePositionResponse(**data)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get gate position stats")
        raise HTTPException(
            status_code=500,
            detail="枠順統計データの取得に失敗しました"
        )


@app.get("/statistics/past-races", response_model=PastStatsResponse)
def get_past_race_stats(
    track_code: str = Query(..., description='トラックコード（"1": 芝コース, "2": ダートコース, "3": 障害コース）'),
    distance: int = Query(..., description="距離（メートル）"),
    grade_code: str | None = Query(None, description="グレードコード"),
    limit: int = Query(100, ge=10, le=500, description="集計対象レース数"),
):
    """過去の同コース・同距離のレース統計を取得."""
    try:
        stats = db.get_past_race_statistics(
            track_code=track_code,
            distance=distance,
            grade_code=grade_code,
            limit_races=limit
        )

        if not stats:
            raise HTTPException(
                status_code=404,
                detail="統計データが見つかりませんでした"
            )

        return PastStatsResponse(
            total_races=stats["total_races"],
            popularity_stats=[
                PopularityStatResponse(**stat)
                for stat in stats["popularity_stats"]
            ],
            avg_win_payout=stats["avg_win_payout"],
            avg_place_payout=stats["avg_place_payout"],
            conditions=stats["conditions"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get past statistics")
        raise HTTPException(
            status_code=500,
            detail="統計データの取得に失敗しました"
        )


@app.get("/statistics/jockey-course", response_model=JockeyCourseStatsResponse)
def get_jockey_course_stats(
    jockey_id: str = Query(..., description="騎手コード"),
    track_code: str = Query(..., description='トラックコード（"1": 芝, "2": ダート, "3": 障害）'),
    distance: int = Query(..., description="距離（メートル）"),
    keibajo_code: str | None = Query(None, description="競馬場コード（01-10）"),
    limit: int = Query(100, ge=10, le=500, description="集計対象レース数"),
):
    """騎手の特定コースでの成績を取得."""
    try:
        stats = db.get_jockey_course_stats(
            jockey_id=jockey_id,
            track_code=track_code,
            distance=distance,
            keibajo_code=keibajo_code,
            limit_races=limit,
        )

        if not stats:
            raise HTTPException(
                status_code=404,
                detail="騎手成績データが見つかりませんでした"
            )

        return JockeyCourseStatsResponse(
            jockey_id=stats["jockey_id"],
            jockey_name=stats["jockey_name"],
            total_rides=stats["total_rides"],
            wins=stats["wins"],
            places=stats["places"],
            win_rate=stats["win_rate"],
            place_rate=stats["place_rate"],
            conditions=stats["conditions"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get jockey course stats")
        raise HTTPException(
            status_code=500,
            detail="騎手成績データの取得に失敗しました"
        )


@app.get("/statistics/popularity-payout", response_model=PopularityPayoutResponse)
def get_popularity_payout_stats(
    track_code: str = Query(..., description='トラックコード（"1": 芝, "2": ダート, "3": 障害）'),
    distance: int = Query(..., description="距離（メートル）"),
    popularity: int = Query(..., ge=1, le=18, description="人気順（1-18）"),
    limit: int = Query(100, ge=10, le=500, description="集計対象レース数"),
):
    """特定人気の配当統計を取得."""
    try:
        stats = db.get_popularity_payout_stats(
            track_code=track_code,
            distance=distance,
            popularity=popularity,
            limit_races=limit,
        )

        if not stats:
            raise HTTPException(
                status_code=404,
                detail="配当統計データが見つかりませんでした"
            )

        return PopularityPayoutResponse(
            popularity=stats["popularity"],
            total_races=stats["total_races"],
            win_count=stats["win_count"],
            avg_win_payout=stats["avg_win_payout"],
            avg_place_payout=stats["avg_place_payout"],
            estimated_roi_win=stats["estimated_roi_win"],
            estimated_roi_place=stats["estimated_roi_place"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get popularity payout stats")
        raise HTTPException(
            status_code=500,
            detail="配当統計データの取得に失敗しました"
        )


@app.get("/jockeys/{jockey_id}/info", response_model=JockeyInfoResponse)
def get_jockey_info(jockey_id: str):
    """騎手基本情報を取得する."""
    try:
        info = db.get_jockey_info(jockey_id)

        if not info:
            raise HTTPException(
                status_code=404,
                detail="騎手情報が見つかりませんでした"
            )

        return JockeyInfoResponse(
            jockey_id=info["jockey_id"],
            jockey_name=info["jockey_name"],
            jockey_name_kana=info.get("jockey_name_kana"),
            birth_date=info.get("birth_date"),
            affiliation=info.get("affiliation"),
            license_year=info.get("license_year"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get jockey info")
        raise HTTPException(
            status_code=500,
            detail="騎手情報の取得に失敗しました"
        )


@app.get("/jockeys/{jockey_id}/stats", response_model=JockeyStatsResponse)
def get_jockey_stats(
    jockey_id: str,
    year: int | None = Query(
        None,
        ge=1900,
        le=2100,
        description="年（指定時はその年の成績）",
    ),
    period: str = Query("recent", description="期間（recent=直近1年, ytd=今年初から, all=通算）"),
):
    """騎手の成績統計を取得する."""
    # period のバリデーション
    valid_periods = ["recent", "ytd", "all"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"period は {', '.join(valid_periods)} のいずれかで指定してください"
        )

    try:
        stats = db.get_jockey_stats(
            jockey_id=jockey_id,
            year=year,
            period=period,
        )

        if not stats:
            raise HTTPException(
                status_code=404,
                detail="騎手成績データが見つかりませんでした"
            )

        return JockeyStatsResponse(
            jockey_id=stats["jockey_id"],
            jockey_name=stats["jockey_name"],
            total_rides=stats["total_rides"],
            wins=stats["wins"],
            second_places=stats["second_places"],
            third_places=stats["third_places"],
            win_rate=stats["win_rate"],
            place_rate=stats["place_rate"],
            period=stats["period"],
            year=stats.get("year"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get jockey stats")
        raise HTTPException(
            status_code=500,
            detail="騎手成績データの取得に失敗しました"
        )


# ========================================
# IPAT投票モデル
# ========================================


class IpatBetLineRequest(BaseModel):
    """IPAT投票行リクエスト."""
    opdt: str
    rcoursecd: str
    rno: str
    denomination: str
    method: str
    multi: str
    number: str
    bet_price: str


class IpatVoteRequest(BaseModel):
    """IPAT投票リクエスト."""
    inet_id: str
    subscriber_number: str
    pin: str
    pars_number: str
    bet_lines: list[IpatBetLineRequest]


class IpatStatRequest(BaseModel):
    """IPAT残高照会リクエスト."""
    inet_id: str
    subscriber_number: str
    pin: str
    pars_number: str


# ========================================
# IPATエンドポイント
# ========================================

from ipat_executor import IpatExecutor


@app.post("/ipat/vote")
def ipat_vote(request: IpatVoteRequest):
    """IPAT投票を実行する."""
    executor = IpatExecutor()
    bet_lines = [line.model_dump() for line in request.bet_lines]
    return executor.vote(
        request.inet_id,
        request.subscriber_number,
        request.pin,
        request.pars_number,
        bet_lines,
    )


@app.post("/ipat/stat")
def ipat_stat(request: IpatStatRequest):
    """IPAT残高照会を実行する."""
    executor = IpatExecutor()
    return executor.stat(
        request.inet_id,
        request.subscriber_number,
        request.pin,
        request.pars_number,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
