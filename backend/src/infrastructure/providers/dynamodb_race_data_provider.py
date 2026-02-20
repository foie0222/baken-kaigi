"""DynamoDB レースデータプロバイダー.

DynamoDB テーブルからレース・出走馬データを取得する。
"""

from datetime import date, datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Attr, Key

from src.domain.identifiers import RaceId
from src.domain.ports import RaceData, RaceDataProvider, RunnerData

JST = timezone(timedelta(hours=9))

_CONDITION_CODE_MAP = {"1": "良", "2": "稍重", "3": "重", "4": "不良"}


class DynamoDbRaceDataProvider(RaceDataProvider):
    """DynamoDB からレースデータを取得するプロバイダー."""

    def __init__(
        self,
        *,
        races_table=None,
        runners_table=None,
        races_table_name: str = "baken-kaigi-races",
        runners_table_name: str = "baken-kaigi-runners",
    ) -> None:
        """初期化.

        Args:
            races_table: racesテーブルオブジェクト（テスト用DI）
            runners_table: runnersテーブルオブジェクト（テスト用DI）
            races_table_name: racesテーブル名
            runners_table_name: runnersテーブル名
        """
        if races_table is not None:
            self._races_table = races_table
        else:
            self._races_table = boto3.resource("dynamodb").Table(races_table_name)

        if runners_table is not None:
            self._runners_table = runners_table
        else:
            self._runners_table = boto3.resource("dynamodb").Table(runners_table_name)

    def get_race(self, race_id: RaceId) -> RaceData | None:
        """レース情報を取得する."""
        race_date = str(race_id)[:8]
        response = self._races_table.get_item(
            Key={"race_date": race_date, "race_id": str(race_id)}
        )
        item = response.get("Item")
        if item is None:
            return None
        return self._to_race_data(item)

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        """出走馬情報を取得する."""
        response = self._runners_table.query(
            KeyConditionExpression=Key("race_id").eq(str(race_id))
        )
        items = response.get("Items", [])
        runners = [self._to_runner_data(item) for item in items]
        runners.sort(key=lambda r: r.horse_number)
        return runners

    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        """日付でレース一覧を取得する.

        Args:
            target_date: 対象日付
            venue: 競馬場コード（例: "05"=東京）。Noneの場合は全開催場。
        """
        race_date = target_date.strftime("%Y%m%d")
        response = self._races_table.query(
            KeyConditionExpression=Key("race_date").eq(race_date)
        )
        items = response.get("Items", [])
        if venue is not None:
            items = [item for item in items if item.get("venue_code") == venue]
        races = [self._to_race_data(item) for item in items]
        races.sort(key=lambda r: (r.venue, r.race_number))
        return races

    # ------------------------------------------------------------------
    # 変換ヘルパー
    # ------------------------------------------------------------------

    def _to_race_data(self, item: dict) -> RaceData:
        """DynamoDB アイテムを RaceData に変換する."""
        race_date = item["race_date"]
        post_time = item.get("post_time", "")
        start_time = self._parse_start_time(race_date, post_time)

        track_type = item.get("track_type", "")
        track_condition = self._resolve_track_condition(
            track_type,
            item.get("turf_condition_code", ""),
            item.get("dirt_condition_code", ""),
        )

        return RaceData(
            race_id=item["race_id"],
            race_name=item["race_name"],
            race_number=int(item["race_number"]),
            venue=item["venue_code"],
            start_time=start_time,
            betting_deadline=start_time - timedelta(minutes=2),
            track_condition=track_condition,
            track_type=track_type,
            distance=int(item.get("distance", 0)),
            horse_count=int(item.get("horse_count", 0)),
            grade_class=item.get("grade", ""),
            is_obstacle=track_type == "障害",
            kaisai_kai=item.get("kaisai_kai", ""),
            kaisai_nichime=item.get("kaisai_nichime", ""),
            age_condition="",
        )

    @staticmethod
    def _parse_start_time(race_date: str, post_time: str) -> datetime:
        """race_date と post_time から datetime(JST) を生成する."""
        if len(post_time) == 4 and post_time.isdigit():
            hour = int(post_time[:2])
            minute = int(post_time[2:])
            year = int(race_date[:4])
            month = int(race_date[4:6])
            day = int(race_date[6:8])
            return datetime(year, month, day, hour, minute, tzinfo=JST)
        return datetime.now(JST)

    @staticmethod
    def _resolve_track_condition(
        track_type: str,
        turf_condition_code: str,
        dirt_condition_code: str,
    ) -> str:
        """馬場状態コードを文字列に変換する."""
        if track_type in ("ダート", "ダート→芝"):
            code = dirt_condition_code
        else:
            code = turf_condition_code
        return _CONDITION_CODE_MAP.get(code, "")

    @staticmethod
    def _to_runner_data(item: dict) -> RunnerData:
        """DynamoDB アイテムを RunnerData に変換する."""
        return RunnerData(
            horse_number=int(item["horse_number"]),
            horse_name=item["horse_name"],
            horse_id=item["horse_id"],
            jockey_name=item["jockey_name"],
            jockey_id=item["jockey_id"],
            odds=str(item.get("odds", "0")),
            popularity=int(item.get("popularity", 0)),
            waku_ban=int(item.get("waku_ban", 0)),
        )

    # ------------------------------------------------------------------
    # DynamoDB未対応メソッド（データなしとして適切な空値を返す）
    # ------------------------------------------------------------------

    def get_jockey_stats(self, jockey_id, course):
        return None

    def get_pedigree(self, horse_id):
        return None

    def get_weight_history(self, horse_id, limit=5):
        return []

    def get_race_weights(self, race_id):
        return {}

    def get_jra_checksum(self, venue_code, kaisai_kai, kaisai_nichime, race_number):
        return None

    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        """指定期間内の開催日一覧を取得する（降順）."""
        scan_kwargs: dict = {"ProjectionExpression": "race_date"}

        if from_date and to_date:
            scan_kwargs["FilterExpression"] = Attr("race_date").between(
                from_date.strftime("%Y%m%d"), to_date.strftime("%Y%m%d")
            )
        elif from_date:
            scan_kwargs["FilterExpression"] = Attr("race_date").gte(
                from_date.strftime("%Y%m%d")
            )
        elif to_date:
            scan_kwargs["FilterExpression"] = Attr("race_date").lte(
                to_date.strftime("%Y%m%d")
            )

        dates: set[date] = set()
        response = self._races_table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            rd = item["race_date"]
            dates.add(date(int(rd[:4]), int(rd[4:6]), int(rd[6:8])))

        while "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = self._races_table.scan(**scan_kwargs)
            for item in response.get("Items", []):
                rd = item["race_date"]
                dates.add(date(int(rd[:4]), int(rd[4:6]), int(rd[6:8])))

        return sorted(dates, reverse=True)

    def get_past_race_stats(self, track_type, distance, grade_class=None, limit=100):
        return None

    def get_jockey_info(self, jockey_id):
        return None

    def get_jockey_stats_detail(self, jockey_id, year=None, period="recent"):
        return None

    def get_horse_performances(self, horse_id, limit=5, track_type=None):
        return []

    def get_horse_training(self, horse_id, limit=5, days=30):
        return [], None

    def get_extended_pedigree(self, horse_id):
        return None

    def get_odds_history(self, race_id):
        return None

    def get_running_styles(self, race_id):
        return []

    def get_course_aptitude(self, horse_id):
        return None

    def get_trainer_info(self, trainer_id):
        return None

    def get_trainer_stats_detail(self, trainer_id, year=None, period="all"):
        return None, [], []

    def get_stallion_offspring_stats(self, stallion_id, year=None, track_type=None):
        return None, [], [], [], []

    def get_gate_position_stats(
        self, venue, track_type=None, distance=None, track_condition=None, limit=100
    ):
        return None

    def get_race_results(self, race_id):
        return None

    def get_owner_info(self, owner_id):
        return None

    def get_owner_stats(self, owner_id, year=None, period="all"):
        return None

    def get_breeder_info(self, breeder_id):
        return None

    def get_breeder_stats(self, breeder_id, year=None, period="all"):
        return None

    def get_all_odds(self, race_id):
        return None
