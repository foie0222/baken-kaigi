"""JRAチェックサム自動更新 Lambda handler.

EventBridgeから毎朝トリガーされ、EC2上のjravan-apiに
POST /jra-checksum/auto-update リクエストを送信して
JRA出馬表のチェックサムを自動更新する。

接続エラー時は指数バックオフでリトライする。
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JST = timezone(timedelta(hours=9))
REQUEST_TIMEOUT = 290  # スクレイピング処理は最大数分かかるため余裕を持たせる
MAX_RETRIES = 3
RETRY_BASE_DELAY = 5
RETRYABLE_STATUS_CODES = {502, 503, 504}


def handler(event: dict, context: Any) -> dict:
    """Lambda ハンドラー.

    Args:
        event: Lambda イベント（EventBridgeからのスケジュールイベント）
        context: Lambda コンテキスト

    Returns:
        dict: 実行結果
    """
    logger.info(f"Starting JRA checksum updater: event={event}")

    jravan_api_url = os.environ.get("JRAVAN_API_URL")
    if not jravan_api_url:
        logger.error("JRAVAN_API_URL environment variable is not set")
        return {
            "statusCode": 500,
            "body": {"success": False, "error": "JRAVAN_API_URL not configured"},
        }

    # 対象日付（当日JST）
    target_date = datetime.now(JST).strftime("%Y%m%d")

    url = f"{jravan_api_url}/jra-checksum/auto-update?target_date={target_date}"
    logger.info(f"Sending POST to {url}")

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, timeout=REQUEST_TIMEOUT)
            if response.status_code in RETRYABLE_STATUS_CODES:
                raise requests.ConnectionError(
                    f"Server returned {response.status_code}"
                )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Auto-update completed (attempt {attempt}): {result}")

            return {
                "statusCode": 200,
                "body": {
                    "success": True,
                    "target_date": target_date,
                    "result": result,
                },
            }
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    f"Retryable error (attempt {attempt}/{MAX_RETRIES}): {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Failed after {MAX_RETRIES} attempts: {e}"
                )
        except requests.RequestException as e:
            logger.exception(f"Failed to call jravan-api: {e}")
            return {
                "statusCode": 500,
                "body": {
                    "success": False,
                    "error": str(e),
                },
            }

    return {
        "statusCode": 500,
        "body": {
            "success": False,
            "error": f"Failed after {MAX_RETRIES} retries: {last_error}",
        },
    }
