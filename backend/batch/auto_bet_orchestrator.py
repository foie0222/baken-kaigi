"""自動投票 Orchestrator Lambda.

15分間隔で起動。DynamoDB racesテーブルから当日レース一覧を取得し、
発走5分前の one-time スケジュールを EventBridge Scheduler で動的に作成する。
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RACES_TABLE_NAME = os.environ.get("RACES_TABLE_NAME", "baken-kaigi-races")
BET_EXECUTOR_ARN = os.environ.get("BET_EXECUTOR_ARN", "")
SCHEDULER_ROLE_ARN = os.environ.get("SCHEDULER_ROLE_ARN", "")
SCHEDULE_GROUP = os.environ.get("SCHEDULE_GROUP", "default")
MINUTES_BEFORE = 5
JST = timezone(timedelta(hours=9))


def handler(event, context):
    """Lambda ハンドラ."""
    now = datetime.now(timezone.utc)
    today = now.astimezone(JST).strftime("%Y%m%d")
    logger.info("Orchestrator started: date=%s", today)

    races = _get_today_races(today)
    if not races:
        logger.info("レースなし（非開催日）")
        return {"status": "ok", "created": 0, "skipped": 0}

    scheduler = boto3.client("scheduler", region_name="ap-northeast-1")
    created, skipped = 0, 0

    try:
        for race in races:
            race_id = race["race_id"]
            name = _schedule_name(race_id)

            start_time = datetime.fromisoformat(race["start_time"])
            fire_at = start_time - timedelta(minutes=MINUTES_BEFORE)

            if fire_at <= now:
                skipped += 1
                continue

            if _schedule_exists(scheduler, name):
                skipped += 1
                continue

            _create_schedule(scheduler, name, fire_at, race_id)
            created += 1
    except Exception:
        logger.exception("Orchestrator failed: date=%s", today)
        raise

    logger.info("完了: created=%d, skipped=%d, total=%d", created, skipped, len(races))
    return {"status": "ok", "created": created, "skipped": skipped}


def _schedule_name(race_id: str) -> str:
    return f"auto-bet-{race_id}"


def _get_today_races(date_str: str) -> list[dict]:
    """DynamoDB races テーブルから当日のレース一覧を取得."""
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    table = dynamodb.Table(RACES_TABLE_NAME)
    resp = table.query(
        KeyConditionExpression=Key("race_date").eq(date_str),
    )
    races = []
    for item in resp.get("Items", []):
        post_time = item.get("post_time", "")
        if not post_time or len(post_time) < 4 or not post_time[:4].isdigit():
            continue
        hour = int(post_time[:2])
        minute = int(post_time[2:4])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            continue
        dt = datetime(
            int(date_str[:4]),
            int(date_str[4:6]),
            int(date_str[6:8]),
            hour,
            minute,
            tzinfo=JST,
        )
        races.append({"race_id": item["race_id"], "start_time": dt.isoformat()})
    return races


def _schedule_exists(scheduler, name: str) -> bool:
    """EventBridge Schedule が既に存在するか."""
    try:
        scheduler.get_schedule(Name=name, GroupName=SCHEDULE_GROUP)
        return True
    except scheduler.exceptions.ResourceNotFoundException:
        return False


def _create_schedule(scheduler, name: str, fire_at: datetime, race_id: str):
    """EventBridge one-time schedule を作成."""
    schedule_expression = f"at({fire_at.strftime('%Y-%m-%dT%H:%M:%S')})"
    scheduler.create_schedule(
        Name=name,
        GroupName=SCHEDULE_GROUP,
        ScheduleExpression=schedule_expression,
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": BET_EXECUTOR_ARN,
            "RoleArn": SCHEDULER_ROLE_ARN,
            "Input": json.dumps({"race_id": race_id}),
        },
        ActionAfterCompletion="DELETE",
        State="ENABLED",
    )
    logger.info("Schedule created: %s at %s for %s", name, fire_at, race_id)
