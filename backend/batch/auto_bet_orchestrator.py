"""自動投票 Orchestrator Lambda.

15分間隔で起動。当日レース一覧を取得し、
発走5分前の one-time スケジュールを EventBridge Scheduler で動的に作成する。
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JRAVAN_API_URL = os.environ.get("JRAVAN_API_URL", "http://10.0.1.100:8000")
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

    logger.info("完了: created=%d, skipped=%d, total=%d", created, skipped, len(races))
    return {"status": "ok", "created": created, "skipped": skipped}


def _schedule_name(race_id: str) -> str:
    return f"auto-bet-{race_id}"


def _get_today_races(date_str: str) -> list[dict]:
    """JRA-VAN API からレース一覧を取得."""
    resp = requests.get(f"{JRAVAN_API_URL}/races", params={"date": date_str}, timeout=30)
    resp.raise_for_status()
    return resp.json()


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
