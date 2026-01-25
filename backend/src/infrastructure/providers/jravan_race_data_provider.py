"""JRA-VAN Data Lab. レースデータプロバイダー.

EC2 Windows 上の FastAPI サーバー経由で JV-Link からデータを取得する。
"""
import logging
import os
from datetime import date, datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.domain.identifiers import RaceId
from src.domain.ports import (
    HorsePerformanceData,
    JockeyInfoData,
    JockeyStatsData,
    JockeyStatsDetailData,
    PastRaceStats,
    PedigreeData,
    PerformanceData,
    PopularityStats,
    RaceData,
    RaceDataProvider,
    RunnerData,
    TrainingRecordData,
    TrainingSummaryData,
    WeightData,
)

logger = logging.getLogger(__name__)


class JraVanRaceDataProvider(RaceDataProvider):
    """JRA-VAN Data Lab. からレースデータを取得するプロバイダー.

    EC2 Windows 上の FastAPI サーバーと HTTP 通信してデータを取得する。
    """

    DEFAULT_TIMEOUT = 30  # seconds

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        """初期化.

        Args:
            base_url: FastAPI サーバーの URL (例: http://10.0.1.100:8000)
            timeout: リクエストタイムアウト秒数
        """
        self._base_url = base_url or os.environ.get(
            "JRAVAN_API_URL", "http://10.0.1.100:8000"
        )
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """リトライ機能付きの HTTP セッションを作成する."""
        session = requests.Session()

        # リトライ設定
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def get_race(self, race_id: RaceId) -> RaceData | None:
        """レース情報を取得する."""
        try:
            response = self._session.get(
                f"{self._base_url}/races/{race_id.value}",
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._to_race_data(response.json())
        except requests.RequestException as e:
            logger.error(f"Failed to get race {race_id}: {e}")
            raise JraVanApiError(f"Failed to get race: {e}") from e

    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        """日付でレース一覧を取得する."""
        try:
            params = {"date": target_date.strftime("%Y%m%d")}
            if venue:
                params["venue"] = venue

            response = self._session.get(
                f"{self._base_url}/races",
                params=params,
                timeout=self._timeout,
            )
            response.raise_for_status()

            races_data = response.json()
            return [self._to_race_data(r) for r in races_data]
        except requests.RequestException as e:
            logger.error(f"Failed to get races for {target_date}: {e}")
            raise JraVanApiError(f"Failed to get races: {e}") from e

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        """出走馬情報を取得する."""
        try:
            response = self._session.get(
                f"{self._base_url}/races/{race_id.value}/runners",
                timeout=self._timeout,
            )
            response.raise_for_status()

            runners_data = response.json()
            return [self._to_runner_data(r) for r in runners_data]
        except requests.RequestException as e:
            logger.error(f"Failed to get runners for {race_id}: {e}")
            raise JraVanApiError(f"Failed to get runners: {e}") from e

    def get_past_performance(self, horse_id: str) -> list[PerformanceData]:
        """馬の過去成績を取得する.

        注意: 現在のAPIでは未実装のため、空リストを返す。
        """
        try:
            response = self._session.get(
                f"{self._base_url}/horses/{horse_id}/performances",
                timeout=self._timeout,
            )
            if response.status_code == 404:
                # エンドポイント未実装の場合は空リストを返す
                return []
            response.raise_for_status()

            performances_data = response.json()
            return [self._to_performance_data(p) for p in performances_data]
        except requests.RequestException as e:
            # API未実装やネットワークエラーの場合は空リストを返す
            logger.warning(f"Could not get performances for horse {horse_id}: {e}")
            return []

    def get_jockey_stats(self, jockey_id: str, course: str) -> JockeyStatsData | None:
        """騎手のコース成績を取得する.

        注意: 現在のAPIでは未実装のため、Noneを返す。
        """
        try:
            response = self._session.get(
                f"{self._base_url}/jockeys/{jockey_id}/stats",
                params={"course": course},
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._to_jockey_stats_data(response.json())
        except requests.RequestException as e:
            # API未実装やネットワークエラーの場合はNoneを返す
            logger.warning(f"Could not get stats for jockey {jockey_id}: {e}")
            return None

    def _to_race_data(self, data: dict) -> RaceData:
        """API レスポンスを RaceData に変換する."""
        # start_time / betting_deadline が None の場合はダミー値を使用
        start_time = (
            datetime.fromisoformat(data["start_time"])
            if data.get("start_time")
            else datetime.now()
        )
        betting_deadline = (
            datetime.fromisoformat(data["betting_deadline"])
            if data.get("betting_deadline")
            else start_time
        )
        return RaceData(
            race_id=data["race_id"],
            race_name=data["race_name"],
            race_number=data["race_number"],
            venue=data["venue"],
            start_time=start_time,
            betting_deadline=betting_deadline,
            track_condition=data["track_condition"],
            track_type=data.get("track_type", ""),
            distance=data.get("distance", 0),
            horse_count=data.get("horse_count", 0),
            # 条件フィールド
            grade_class=data.get("grade_class", ""),
            age_condition=data.get("age_condition", ""),
            is_obstacle=data.get("is_obstacle", False),
            # JRA出馬表URL生成用
            kaisai_kai=data.get("kaisai_kai", ""),
            kaisai_nichime=data.get("kaisai_nichime", ""),
        )

    def _to_runner_data(self, data: dict) -> RunnerData:
        """API レスポンスを RunnerData に変換する."""
        return RunnerData(
            horse_number=data["horse_number"],
            horse_name=data["horse_name"],
            horse_id=data["horse_id"],
            jockey_name=data["jockey_name"],
            jockey_id=data["jockey_id"],
            odds=data["odds"],
            popularity=data["popularity"],
            waku_ban=data.get("waku_ban", 0),
        )

    def _to_performance_data(self, data: dict) -> PerformanceData:
        """API レスポンスを PerformanceData に変換する."""
        return PerformanceData(
            race_date=datetime.fromisoformat(data["race_date"]),
            race_name=data["race_name"],
            venue=data["venue"],
            finish_position=data["finish_position"],
            distance=data["distance"],
            track_condition=data["track_condition"],
            time=data["time"],
        )

    def _to_jockey_stats_data(self, data: dict) -> JockeyStatsData:
        """API レスポンスを JockeyStatsData に変換する."""
        return JockeyStatsData(
            jockey_id=data["jockey_id"],
            jockey_name=data["jockey_name"],
            course=data["course"],
            total_races=data["total_races"],
            wins=data["wins"],
            win_rate=data["win_rate"],
            place_rate=data["place_rate"],
        )

    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        """馬の血統情報を取得する."""
        try:
            response = self._session.get(
                f"{self._base_url}/horses/{horse_id}/pedigree",
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._to_pedigree_data(response.json())
        except requests.RequestException as e:
            logger.warning(f"Could not get pedigree for horse {horse_id}: {e}")
            return None

    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        """馬の体重履歴を取得する."""
        try:
            response = self._session.get(
                f"{self._base_url}/horses/{horse_id}/weights",
                params={"limit": limit},
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()

            weights_data = response.json()
            return [self._to_weight_data(w) for w in weights_data]
        except requests.RequestException as e:
            logger.warning(f"Could not get weight history for horse {horse_id}: {e}")
            return []

    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        """レースの馬体重情報を取得する."""
        try:
            response = self._session.get(
                f"{self._base_url}/races/{race_id.value}/weights",
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return {}
            response.raise_for_status()

            weights_data = response.json()
            return {
                w["horse_number"]: WeightData(
                    weight=w["weight"],
                    weight_diff=w["weight_diff"],
                )
                for w in weights_data
            }
        except requests.RequestException as e:
            logger.warning(f"Could not get race weights for {race_id}: {e}")
            return {}

    def _to_pedigree_data(self, data: dict) -> PedigreeData:
        """API レスポンスを PedigreeData に変換する."""
        return PedigreeData(
            horse_id=data["horse_id"],
            horse_name=data.get("horse_name"),
            sire_name=data.get("sire_name"),
            dam_name=data.get("dam_name"),
            broodmare_sire=data.get("broodmare_sire"),
        )

    def _to_weight_data(self, data: dict) -> WeightData:
        """API レスポンスを WeightData に変換する."""
        return WeightData(
            weight=data["weight"],
            weight_diff=data["weight_diff"],
        )

    def _to_horse_performance_data(self, data: dict) -> HorsePerformanceData:
        """APIレスポンスをHorsePerformanceDataに変換する."""
        return HorsePerformanceData(
            race_id=data["race_id"],
            race_date=data["race_date"],
            race_name=data["race_name"],
            venue=data["venue"],
            distance=data["distance"],
            track_type=data["track_type"],
            track_condition=data["track_condition"],
            finish_position=data["finish_position"],
            total_runners=data["total_runners"],
            time=data["time"],
            horse_name=data.get("horse_name"),
            time_diff=data.get("time_diff"),
            last_3f=data.get("last_3f"),
            weight_carried=data.get("weight_carried"),
            jockey_name=data.get("jockey_name"),
            odds=data.get("odds"),
            popularity=data.get("popularity"),
            margin=data.get("margin"),
            race_pace=data.get("race_pace"),
            running_style=data.get("running_style"),
        )

    def get_horse_performances(
        self,
        horse_id: str,
        limit: int = 5,
        track_type: str | None = None,
    ) -> list[HorsePerformanceData]:
        """馬の過去成績を詳細に取得する."""
        try:
            params: dict[str, str | int] = {"limit": min(limit, 20)}
            if track_type:
                params["track_type"] = track_type

            response = self._session.get(
                f"{self._base_url}/horses/{horse_id}/performances",
                params=params,
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()

            performances_data = response.json()
            return [self._to_horse_performance_data(p) for p in performances_data]
        except requests.RequestException as e:
            logger.warning(f"Could not get performances for horse {horse_id}: {e}")
            return []

    def get_jra_checksum(
        self,
        venue_code: str,
        kaisai_kai: str,
        kaisai_nichime: int,
        race_number: int,
    ) -> int | None:
        """JRA出馬表URLのチェックサムを取得する."""
        try:
            response = self._session.get(
                f"{self._base_url}/jra-checksum",
                params={
                    "venue_code": venue_code,
                    "kaisai_kai": kaisai_kai,
                    "kaisai_nichime": kaisai_nichime,
                    "race_number": race_number,
                },
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("checksum")
        except requests.RequestException as e:
            logger.warning(
                f"Could not get JRA checksum for {venue_code}/{kaisai_kai}: {e}"
            )
            return None


    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        """開催日一覧を取得する."""
        try:
            params = {}
            if from_date:
                params["from_date"] = from_date.strftime("%Y%m%d")
            if to_date:
                params["to_date"] = to_date.strftime("%Y%m%d")

            response = self._session.get(
                f"{self._base_url}/race-dates",
                params=params,
                timeout=self._timeout,
            )
            response.raise_for_status()

            dates_data = response.json()
            return [
                datetime.strptime(d, "%Y%m%d").date()
                for d in dates_data
            ]
        except requests.RequestException as e:
            logger.warning(f"Could not get race dates: {e}")
            return []

    def get_past_race_stats(
        self,
        track_type: str,
        distance: int,
        grade_class: str | None = None,
        limit: int = 100
    ) -> PastRaceStats | None:
        """過去の同条件レース統計を取得する."""
        try:
            # トラック種別をコードに変換
            track_code = self._to_track_code(track_type)

            response = self._session.get(
                f"{self._base_url}/statistics/past-races",
                params={
                    "track_code": track_code,
                    "distance": distance,
                    "grade_code": grade_class,
                    "limit": limit,
                },
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._to_past_stats_data(response.json())
        except requests.RequestException as e:
            logger.warning(f"Could not get past race stats: {e}")
            return None

    def _to_track_code(self, track_type: str) -> str:
        """トラック種別をAPIのtrack_codeに変換する."""
        track_map = {
            "芝": "1",
            "ダート": "2",
            "ダ": "2",
            "障害": "3",
        }
        return track_map.get(track_type, "1")

    def _to_past_stats_data(self, data: dict) -> PastRaceStats:
        """APIレスポンスをPastRaceStatsに変換する."""
        # track_codeを日本語表記に変換
        track_code = data["conditions"]["track_code"]
        track_type_map = {"1": "芝", "2": "ダート", "3": "障害"}
        track_type = track_type_map.get(track_code, track_code)

        return PastRaceStats(
            total_races=data["total_races"],
            popularity_stats=[
                PopularityStats(
                    popularity=stat["popularity"],
                    total_runs=stat["total_runs"],
                    wins=stat["wins"],
                    places=stat["places"],
                    win_rate=stat["win_rate"],
                    place_rate=stat["place_rate"],
                )
                for stat in data["popularity_stats"]
            ],
            avg_win_payout=data.get("avg_win_payout"),
            avg_place_payout=data.get("avg_place_payout"),
            track_type=track_type,
            distance=data["conditions"]["distance"],
            grade_class=data["conditions"].get("grade_code"),
        )

    def get_jockey_info(self, jockey_id: str) -> JockeyInfoData | None:
        """騎手基本情報を取得する."""
        try:
            response = self._session.get(
                f"{self._base_url}/jockeys/{jockey_id}/info",
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._to_jockey_info_data(response.json())
        except requests.RequestException as e:
            logger.warning(f"Could not get jockey info for {jockey_id}: {e}")
            return None

    def get_jockey_stats_detail(
        self,
        jockey_id: str,
        year: int | None = None,
        period: str = "recent",
    ) -> JockeyStatsDetailData | None:
        """騎手の成績統計を取得する."""
        try:
            params = {"period": period}
            if year is not None:
                params["year"] = year

            response = self._session.get(
                f"{self._base_url}/jockeys/{jockey_id}/stats",
                params=params,
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._to_jockey_stats_detail_data(response.json())
        except requests.RequestException as e:
            logger.warning(f"Could not get jockey stats for {jockey_id}: {e}")
            return None

    def _to_jockey_info_data(self, data: dict) -> JockeyInfoData:
        """APIレスポンスをJockeyInfoDataに変換する."""
        return JockeyInfoData(
            jockey_id=data["jockey_id"],
            jockey_name=data["jockey_name"],
            jockey_name_kana=data.get("jockey_name_kana"),
            birth_date=data.get("birth_date"),
            affiliation=data.get("affiliation"),
            license_year=data.get("license_year"),
        )

    def _to_jockey_stats_detail_data(self, data: dict) -> JockeyStatsDetailData:
        """APIレスポンスをJockeyStatsDetailDataに変換する."""
        return JockeyStatsDetailData(
            jockey_id=data["jockey_id"],
            jockey_name=data["jockey_name"],
            total_rides=data["total_rides"],
            wins=data["wins"],
            second_places=data["second_places"],
            third_places=data["third_places"],
            win_rate=data["win_rate"],
            place_rate=data["place_rate"],
            period=data["period"],
            year=data.get("year"),
        )

    def get_horse_training(
        self,
        horse_id: str,
        limit: int = 5,
        days: int = 30,
    ) -> tuple[list[TrainingRecordData], TrainingSummaryData | None]:
        """馬の調教データを取得する."""
        try:
            params: dict[str, int] = {
                "limit": min(limit, 10),
                "days": days,
            }

            response = self._session.get(
                f"{self._base_url}/horses/{horse_id}/training",
                params=params,
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return [], None
            response.raise_for_status()

            data = response.json()
            records = [self._to_training_record_data(r) for r in data.get("training_records", [])]
            summary = None
            if data.get("training_summary"):
                summary = self._to_training_summary_data(data["training_summary"])
            return records, summary
        except requests.RequestException as e:
            logger.warning(f"Could not get training data for horse {horse_id}: {e}")
            return [], None

    def _to_training_record_data(self, data: dict) -> TrainingRecordData:
        """APIレスポンスをTrainingRecordDataに変換する."""
        return TrainingRecordData(
            date=data["date"],
            course=data["course"],
            course_condition=data["course_condition"],
            distance=data["distance"],
            time=data["time"],
            last_3f=data.get("last_3f"),
            last_1f=data.get("last_1f"),
            training_type=data.get("training_type"),
            partner_horse=data.get("partner_horse"),
            evaluation=data.get("evaluation"),
            comment=data.get("comment"),
        )

    def _to_training_summary_data(self, data: dict) -> TrainingSummaryData:
        """APIレスポンスをTrainingSummaryDataに変換する."""
        return TrainingSummaryData(
            recent_trend=data["recent_trend"],
            average_time=data.get("average_time"),
            best_time=data.get("best_time"),
        )


class JraVanApiError(Exception):
    """JRA-VAN API エラー."""

    pass
