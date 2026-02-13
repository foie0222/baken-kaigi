"""EC2 スケジューラー Lambda ハンドラー.

EventBridge Scheduler から呼び出され、EC2 インスタンスの起動/停止を行う。
"""
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ec2 = boto3.client("ec2", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))


def handler(event, context):
    """EC2 インスタンスを起動または停止する.

    Args:
        event: EventBridge からのイベント。action フィールドで操作を指定。
        context: Lambda コンテキスト。

    Returns:
        操作結果を含む dict。
    """
    instance_id = os.environ.get("INSTANCE_ID")
    if not instance_id:
        logger.error("INSTANCE_ID environment variable is not set")
        return {"status": "error", "message": "INSTANCE_ID environment variable is not set"}

    action = event.get("action", "")

    if action == "start":
        try:
            ec2.start_instances(InstanceIds=[instance_id])
            logger.info("Starting instance %s", instance_id)
            return {"status": "starting", "instance_id": instance_id}
        except ClientError as e:
            logger.exception("Failed to start instance %s", instance_id)
            return {"status": "error", "message": str(e)}
    elif action == "stop":
        try:
            ec2.stop_instances(InstanceIds=[instance_id])
            logger.info("Stopping instance %s", instance_id)
            return {"status": "stopping", "instance_id": instance_id}
        except ClientError as e:
            logger.exception("Failed to stop instance %s", instance_id)
            return {"status": "error", "message": str(e)}
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}
