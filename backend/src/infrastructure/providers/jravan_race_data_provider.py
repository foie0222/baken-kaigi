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
    JockeyStatsData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
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
        return RaceData(
            race_id=data["race_id"],
            race_name=data["race_name"],
            race_number=data["race_number"],
            venue=data["venue"],
            start_time=datetime.fromisoformat(data["start_time"]),
            betting_deadline=datetime.fromisoformat(data["betting_deadline"]),
            track_condition=data["track_condition"],
            track_type=data.get("track_type", ""),
            distance=data.get("distance", 0),
            horse_count=data.get("horse_count", 0),
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


class JraVanApiError(Exception):
    """JRA-VAN API エラー."""

    pass
