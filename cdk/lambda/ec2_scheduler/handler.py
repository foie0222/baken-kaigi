"""EC2 スケジューラー Lambda ハンドラー.

EventBridge Scheduler から呼び出され、EC2 インスタンスの起動/停止を行う。
"""
import boto3
import os

ec2 = boto3.client("ec2", region_name="ap-northeast-1")


def handler(event, context):
    """EC2 インスタンスを起動または停止する.

    Args:
        event: EventBridge からのイベント。action フィールドで操作を指定。
        context: Lambda コンテキスト。

    Returns:
        操作結果を含む dict。
    """
    instance_id = os.environ["INSTANCE_ID"]
    action = event.get("action", "")

    if action == "start":
        ec2.start_instances(InstanceIds=[instance_id])
        return {"status": "starting", "instance_id": instance_id}
    elif action == "stop":
        ec2.stop_instances(InstanceIds=[instance_id])
        return {"status": "stopping", "instance_id": instance_id}
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}
