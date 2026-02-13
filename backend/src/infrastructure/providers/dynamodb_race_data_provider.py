"""DynamoDB を使用した RaceDataProvider 実装.

HRDB-APIバッチで取り込んだDynamoDBテーブルからレースデータを読み出す。
"""
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import boto3

from src.domain.identifiers import RaceId
from src.domain.ports.race_data_provider import (
    AncestorData,
    AptitudeSummaryData,
    ConditionAptitudeData,
    CourseAptitudeData,
    DistanceAptitudeData,
    ExtendedPedigreeData,
    HorsePerformanceData,
    PedigreeData,
    PerformanceData,
    PositionAptitudeData,
    RaceData,
    RaceDataProvider,
    RaceResultData,
    RaceResultsData,
    RunnerData,
    TrackTypeAptitudeData,
    VenueAptitudeData,
    WeightData,
)

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

# JRA競馬場コード→名称マッピング
VENUE_CODE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}

# 逆引き: 競馬場名→コード
VENUE_NAME_MAP = {v: k for k, v in VENUE_CODE_MAP.items()}

# track_code先頭桁→トラック種別
TRACK_TYPE_MAP = {"1": "芝", "2": "ダート", "5": "障害"}

# grade_code→グレード表示名
GRADE_CODE_MAP = {
    "1": "G1", "2": "G2", "3": "G3",
    "4": "L", "5": "OP",
}

# 馬場状態コード→表示名
TRACK_CONDITION_MAP = {"1": "良", "2": "稍", "3": "重", "4": "不"}


class DynamoDbRaceDataProvider(RaceDataProvider):
    """DynamoDB からレースデータを取得するプロバイダー."""

    def __init__(self, region_name: str = "ap-northeast-1") -> None:
        dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self._races_table = dynamodb.Table("baken-kaigi-races")
        self._runners_table = dynamodb.Table("baken-kaigi-runners")
        self._horses_table = dynamodb.Table("baken-kaigi-horses")
        self._jockeys_table = dynamodb.Table("baken-kaigi-jockeys")
        self._trainers_table = dynamodb.Table("baken-kaigi-trainers")

    # ========================================
    # 基本6メソッド
    # ========================================

    def get_race(self, race_id: RaceId) -> RaceData | None:
        """レース情報を取得する."""
        race_date = race_id.value.split("_")[0]
        resp = self._races_table.query(
            KeyConditionExpression="race_date = :rd AND race_id = :ri",
            ExpressionAttributeValues={
                ":rd": race_date,
                ":ri": race_id.value,
            },
        )
        items = resp.get("Items", [])
        if not items:
            return None
        return self._item_to_race_data(items[0])

    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        """日付でレース一覧を取得する."""
        date_str = target_date.strftime("%Y%m%d")
        resp = self._races_table.query(
            KeyConditionExpression="race_date = :rd",
            ExpressionAttributeValues={":rd": date_str},
        )
        items = resp.get("Items", [])

        if venue:
            venue_code = VENUE_NAME_MAP.get(venue, "")
            items = [i for i in items if i.get("venue_code") == venue_code]

        races = [self._item_to_race_data(item) for item in items]
        races.sort(key=lambda r: (r.venue, r.race_number))
        return races

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        """出走馬情報を取得する."""
        resp = self._runners_table.query(
            KeyConditionExpression="race_id = :ri",
            ExpressionAttributeValues={":ri": race_id.value},
        )
        items = resp.get("Items", [])
        runners = [self._item_to_runner_data(item) for item in items]
        runners.sort(key=lambda r: r.horse_number)
        return runners

    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        """レースの馬体重情報を取得する."""
        resp = self._runners_table.query(
            KeyConditionExpression="race_id = :ri",
            ExpressionAttributeValues={":ri": race_id.value},
        )
        result: dict[int, WeightData] = {}
        for item in resp.get("Items", []):
            if "weight" not in item:
                continue
            horse_number = int(item["horse_number"])
            result[horse_number] = WeightData(
                weight=int(item["weight"]),
                weight_diff=int(item.get("weight_diff", 0)),
            )
        return result

    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        """開催日一覧を取得する."""
        resp = self._races_table.scan(
            ProjectionExpression="race_date",
        )
        items = resp.get("Items", [])
        while resp.get("LastEvaluatedKey"):
            resp = self._races_table.scan(
                ProjectionExpression="race_date",
                ExclusiveStartKey=resp["LastEvaluatedKey"],
            )
            items.extend(resp.get("Items", []))

        date_strings = {item["race_date"] for item in items}
        dates = []
        for ds in date_strings:
            d = datetime.strptime(ds, "%Y%m%d").date()
            if from_date and d < from_date:
                continue
            if to_date and d > to_date:
                continue
            dates.append(d)

        dates.sort(reverse=True)
        return dates

    def get_race_results(self, race_id: RaceId) -> RaceResultsData | None:
        """レース結果を取得する."""
        race_date = race_id.value.split("_")[0]
        race_resp = self._races_table.query(
            KeyConditionExpression="race_date = :rd AND race_id = :ri",
            ExpressionAttributeValues={
                ":rd": race_date,
                ":ri": race_id.value,
            },
        )
        race_items = race_resp.get("Items", [])
        if not race_items:
            return None

        race_item = race_items[0]

        runner_resp = self._runners_table.query(
            KeyConditionExpression="race_id = :ri",
            ExpressionAttributeValues={":ri": race_id.value},
        )
        runner_items = runner_resp.get("Items", [])

        # 確定済みの結果のみ（finish_position > 0）
        finalized = [
            item for item in runner_items
            if int(item.get("finish_position", 0)) > 0
        ]
        if not finalized:
            return None

        results = []
        for item in finalized:
            odds_str = item.get("odds", "")
            results.append(RaceResultData(
                horse_number=int(item["horse_number"]),
                horse_name=item.get("horse_name", ""),
                finish_position=int(item["finish_position"]),
                time=item.get("time") or None,
                margin=None,
                last_3f=item.get("last_3f") or None,
                popularity=int(item["popularity"]) if item.get("popularity") else None,
                odds=float(odds_str) if odds_str else None,
                jockey_name=item.get("jockey_name"),
            ))
        results.sort(key=lambda r: r.finish_position)

        venue_code = race_item.get("venue_code", "")
        return RaceResultsData(
            race_id=race_id.value,
            race_name=race_item.get("race_name", ""),
            race_date=race_date,
            venue=VENUE_CODE_MAP.get(venue_code, venue_code),
            results=results,
            payouts=[],
            is_finalized=True,
        )

    # ========================================
    # 馬系メソッド（Task 10）
    # ========================================

    def get_past_performance(self, horse_id):
        """馬の過去成績を取得する."""
        items = self._query_horse_runners(horse_id)
        if not items:
            return []

        results = []
        for item in items:
            race_id = item.get("race_id", "")
            race_info = self._get_race_info(race_id)
            race_date_str = item.get("race_date", "")
            race_dt = (
                datetime.strptime(race_date_str, "%Y%m%d").replace(tzinfo=JST)
                if len(race_date_str) == 8
                else datetime.now(JST)
            )
            venue_code = race_info.get("venue_code", "")
            condition = str(race_info.get("track_condition", ""))
            results.append(PerformanceData(
                race_date=race_dt,
                race_name=race_info.get("race_name", ""),
                venue=VENUE_CODE_MAP.get(venue_code, venue_code),
                finish_position=int(item.get("finish_position", 0)),
                distance=int(race_info.get("distance", 0)),
                track_condition=TRACK_CONDITION_MAP.get(condition, condition),
                time=item.get("time", ""),
            ))

        results.sort(key=lambda r: r.race_date, reverse=True)
        return results

    def get_horse_performances(self, horse_id, limit=5, track_type=None):
        """馬の過去成績を詳細に取得する."""
        items = self._query_horse_runners(horse_id)
        if not items:
            return []

        # 新しい順にソート
        items.sort(key=lambda i: i.get("race_date", ""), reverse=True)

        results = []
        for item in items:
            if len(results) >= limit:
                break

            race_id = item.get("race_id", "")
            race_info = self._get_race_info(race_id)

            track_code = str(race_info.get("track_code", ""))
            item_track_type = TRACK_TYPE_MAP.get(track_code[:1], "") if track_code else ""

            if track_type and item_track_type != track_type:
                continue

            venue_code = race_info.get("venue_code", "")
            condition = str(race_info.get("track_condition", ""))
            odds_str = item.get("odds", "")

            results.append(HorsePerformanceData(
                race_id=race_id,
                race_date=item.get("race_date", ""),
                race_name=race_info.get("race_name", ""),
                venue=VENUE_CODE_MAP.get(venue_code, venue_code),
                distance=int(race_info.get("distance", 0)),
                track_type=item_track_type,
                track_condition=TRACK_CONDITION_MAP.get(condition, condition),
                finish_position=int(item.get("finish_position", 0)),
                total_runners=int(race_info.get("horse_count", 0)),
                time=item.get("time", ""),
                horse_name=item.get("horse_name"),
                last_3f=item.get("last_3f") or None,
                weight_carried=float(item["weight_carried"]) if item.get("weight_carried") else None,
                jockey_name=item.get("jockey_name"),
                odds=float(odds_str) if odds_str else None,
                popularity=int(item["popularity"]) if item.get("popularity") else None,
            ))

        return results

    def get_pedigree(self, horse_id):
        """馬の血統情報を取得する."""
        item = self._get_horse_info(horse_id)
        if not item:
            return None
        return PedigreeData(
            horse_id=horse_id,
            horse_name=item.get("horse_name"),
            sire_name=item.get("sire_name"),
            dam_name=item.get("dam_name"),
            broodmare_sire=item.get("broodmare_sire"),
        )

    def get_extended_pedigree(self, horse_id):
        """馬の拡張血統情報を取得する."""
        item = self._get_horse_info(horse_id)
        if not item:
            return None
        sire_name = item.get("sire_name")
        dam_name = item.get("dam_name")
        bms = item.get("broodmare_sire")
        return ExtendedPedigreeData(
            horse_id=horse_id,
            horse_name=item.get("horse_name"),
            sire=AncestorData(name=sire_name) if sire_name else None,
            dam=AncestorData(name=dam_name, broodmare_sire=bms) if dam_name else None,
            inbreeding=[],
            lineage_type=None,
        )

    def get_weight_history(self, horse_id, limit=5):
        """馬の体重履歴を取得する."""
        items = self._query_horse_runners(horse_id)
        if not items:
            return []

        items.sort(key=lambda i: i.get("race_date", ""), reverse=True)
        results = []
        for item in items[:limit]:
            if "weight" not in item:
                continue
            results.append(WeightData(
                weight=int(item["weight"]),
                weight_diff=int(item.get("weight_diff", 0)),
            ))
        return results

    def get_course_aptitude(self, horse_id):
        """馬のコース適性を取得する."""
        items = self._query_horse_runners(horse_id)
        if not items:
            return None

        horse_name = None
        horse_info = self._get_horse_info(horse_id)
        if horse_info:
            horse_name = horse_info.get("horse_name")

        # 集計用
        venue_stats: dict[str, dict] = {}
        track_type_stats: dict[str, dict] = {}
        distance_stats: dict[str, dict] = {}
        condition_stats: dict[str, dict] = {}
        position_stats: dict[str, dict] = {}

        for item in items:
            race_info = self._get_race_info(item.get("race_id", ""))
            venue_code = race_info.get("venue_code", "")
            venue = VENUE_CODE_MAP.get(venue_code, venue_code)
            track_code = str(race_info.get("track_code", ""))
            track_type = TRACK_TYPE_MAP.get(track_code[:1], "") if track_code else ""
            condition_code = str(race_info.get("track_condition", ""))
            condition = TRACK_CONDITION_MAP.get(condition_code, condition_code)
            distance = int(race_info.get("distance", 0))
            finish_pos = int(item.get("finish_position", 0))
            waku = int(item.get("waku_ban", 0))

            is_win = finish_pos == 1
            is_place = 1 <= finish_pos <= 3

            # 会場別
            if venue:
                s = venue_stats.setdefault(venue, {"starts": 0, "wins": 0, "places": 0})
                s["starts"] += 1
                s["wins"] += int(is_win)
                s["places"] += int(is_place)

            # トラック種別
            if track_type:
                s = track_type_stats.setdefault(track_type, {"starts": 0, "wins": 0})
                s["starts"] += 1
                s["wins"] += int(is_win)

            # 距離帯
            if distance > 0:
                dist_range = self._distance_range(distance)
                s = distance_stats.setdefault(dist_range, {"starts": 0, "wins": 0})
                s["starts"] += 1
                s["wins"] += int(is_win)

            # 馬場状態
            if condition:
                s = condition_stats.setdefault(condition, {"starts": 0, "wins": 0})
                s["starts"] += 1
                s["wins"] += int(is_win)

            # 枠順
            if waku > 0:
                pos = self._waku_position(waku)
                s = position_stats.setdefault(pos, {"starts": 0, "wins": 0})
                s["starts"] += 1
                s["wins"] += int(is_win)

        by_venue = [
            VenueAptitudeData(
                venue=v, starts=s["starts"], wins=s["wins"], places=s["places"],
                win_rate=s["wins"] / s["starts"] if s["starts"] else 0,
                place_rate=s["places"] / s["starts"] if s["starts"] else 0,
            )
            for v, s in venue_stats.items()
        ]
        by_track = [
            TrackTypeAptitudeData(
                track_type=t, starts=s["starts"], wins=s["wins"],
                win_rate=s["wins"] / s["starts"] if s["starts"] else 0,
            )
            for t, s in track_type_stats.items()
        ]
        by_distance = [
            DistanceAptitudeData(
                distance_range=d, starts=s["starts"], wins=s["wins"],
                win_rate=s["wins"] / s["starts"] if s["starts"] else 0,
            )
            for d, s in distance_stats.items()
        ]
        by_condition = [
            ConditionAptitudeData(
                condition=c, starts=s["starts"], wins=s["wins"],
                win_rate=s["wins"] / s["starts"] if s["starts"] else 0,
            )
            for c, s in condition_stats.items()
        ]
        by_position = [
            PositionAptitudeData(
                position=p, starts=s["starts"], wins=s["wins"],
                win_rate=s["wins"] / s["starts"] if s["starts"] else 0,
            )
            for p, s in position_stats.items()
        ]

        best_venue = max(by_venue, key=lambda x: x.win_rate).venue if by_venue else None
        best_dist = max(by_distance, key=lambda x: x.win_rate).distance_range if by_distance else None

        return CourseAptitudeData(
            horse_id=horse_id,
            horse_name=horse_name,
            by_venue=by_venue,
            by_track_type=by_track,
            by_distance=by_distance,
            by_track_condition=by_condition,
            by_running_position=by_position,
            aptitude_summary=AptitudeSummaryData(
                best_venue=best_venue,
                best_distance=best_dist,
                preferred_condition=None,
                preferred_position=None,
            ),
        )

    # HRDB未サポートメソッド（スタブ）
    def get_horse_training(self, horse_id, limit=5, days=30):
        return ([], None)

    def get_jra_checksum(self, venue_code, kaisai_kai, kaisai_nichime, race_number):
        return None

    # ========================================
    # 人物・統計系メソッド（Task 11 で実装）
    # ========================================

    def get_jockey_stats(self, jockey_id, course):
        return None

    def get_past_race_stats(self, track_type, distance, grade_class=None, limit=100):
        return None

    def get_jockey_info(self, jockey_id):
        return None

    def get_jockey_stats_detail(self, jockey_id, year=None, period="recent"):
        return None

    def get_odds_history(self, race_id):
        return None

    def get_trainer_info(self, trainer_id):
        return None

    def get_trainer_stats_detail(self, trainer_id, year=None, period="all"):
        return (None, [], [])

    def get_stallion_offspring_stats(self, stallion_id, year=None, track_type=None):
        return (None, [], [], [], [])

    def get_gate_position_stats(
        self, venue, track_type=None, distance=None, track_condition=None, limit=100
    ):
        return None

    def get_owner_info(self, owner_id):
        return None

    def get_owner_stats(self, owner_id, year=None, period="all"):
        return None

    def get_breeder_info(self, breeder_id):
        return None

    def get_breeder_stats(self, breeder_id, year=None, period="all"):
        return None

    # ========================================
    # 内部ヘルパー（DynamoDB アクセス）
    # ========================================

    def _query_horse_runners(self, horse_id: str) -> list[dict]:
        """horse_id-index でrunnersテーブルを検索する."""
        resp = self._runners_table.query(
            IndexName="horse_id-index",
            KeyConditionExpression="horse_id = :hid",
            ExpressionAttributeValues={":hid": horse_id},
        )
        return resp.get("Items", [])

    def _get_horse_info(self, horse_id: str) -> dict | None:
        """horsesテーブルから馬情報を取得する."""
        resp = self._horses_table.get_item(
            Key={"horse_id": horse_id, "sk": "info"},
        )
        return resp.get("Item")

    def _get_race_info(self, race_id: str) -> dict:
        """racesテーブルからレース情報を取得する."""
        if not race_id:
            return {}
        race_date = race_id.split("_")[0]
        resp = self._races_table.get_item(
            Key={"race_date": race_date, "race_id": race_id},
        )
        return resp.get("Item", {})

    @staticmethod
    def _distance_range(distance: int) -> str:
        """距離を距離帯文字列に変換する."""
        if distance <= 1400:
            return "~1400m"
        if distance <= 1800:
            return "1400-1800m"
        if distance <= 2200:
            return "1800-2200m"
        return "2200m~"

    @staticmethod
    def _waku_position(waku: int) -> str:
        """枠番を位置カテゴリに変換する."""
        if waku <= 2:
            return "内枠(1-2)"
        if waku <= 4:
            return "中内枠(3-4)"
        if waku <= 6:
            return "中外枠(5-6)"
        return "外枠(7-8)"

    # ========================================
    # 内部変換メソッド
    # ========================================

    def _item_to_race_data(self, item: dict) -> RaceData:
        """DynamoDBアイテムをRaceDataに変換する."""
        venue_code = item.get("venue_code", "")
        venue = VENUE_CODE_MAP.get(venue_code, venue_code)

        track_code = str(item.get("track_code", ""))
        track_type = TRACK_TYPE_MAP.get(track_code[:1], "") if track_code else ""

        condition_code = str(item.get("track_condition", ""))
        track_condition = TRACK_CONDITION_MAP.get(condition_code, condition_code)

        grade_code = str(item.get("grade_code", ""))
        grade_class = GRADE_CODE_MAP.get(grade_code, "")

        # start_time "HHMM" → datetime
        race_date_str = item.get("race_date", "")
        start_time_str = str(item.get("start_time", ""))
        start_time = self._parse_start_time(race_date_str, start_time_str)

        is_obstacle = track_code.startswith("5") if track_code else False

        return RaceData(
            race_id=item.get("race_id", ""),
            race_name=item.get("race_name", ""),
            race_number=int(item.get("race_number", 0)),
            venue=venue,
            start_time=start_time,
            betting_deadline=start_time,
            track_condition=track_condition,
            track_type=track_type,
            distance=int(item.get("distance", 0)),
            horse_count=int(item.get("horse_count", 0)),
            grade_class=grade_class,
            age_condition=item.get("condition_code", ""),
            is_obstacle=is_obstacle,
        )

    def _item_to_runner_data(self, item: dict) -> RunnerData:
        """DynamoDBアイテムをRunnerDataに変換する."""
        return RunnerData(
            horse_number=int(item.get("horse_number", 0)),
            horse_name=item.get("horse_name", ""),
            horse_id=item.get("horse_id", ""),
            jockey_name=item.get("jockey_name", ""),
            jockey_id=item.get("jockey_id", ""),
            odds=item.get("odds", ""),
            popularity=int(item.get("popularity", 0)),
            waku_ban=int(item.get("waku_ban", 0)),
        )

    @staticmethod
    def _parse_start_time(race_date_str: str, time_str: str) -> datetime:
        """YYYYMMDD + HHMM → datetime(JST)."""
        if len(race_date_str) == 8 and len(time_str) >= 4:
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            return datetime(
                int(race_date_str[:4]),
                int(race_date_str[4:6]),
                int(race_date_str[6:8]),
                hour, minute,
                tzinfo=JST,
            )
        return datetime.now(JST)
