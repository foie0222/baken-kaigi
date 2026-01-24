"""JRA-VAN API クライアント共通モジュール.

API Key取得とヘッダー生成のロジックを共通化。
"""

import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# JRA-VAN API 設定
JRAVAN_API_URL = os.environ.get(
    "JRAVAN_API_URL",
    "https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod",
)
JRAVAN_API_KEY = os.environ.get("JRAVAN_API_KEY", "")
JRAVAN_API_KEY_ID = os.environ.get("JRAVAN_API_KEY_ID", "zeq5hh8qp6")

_cached_api_key: str | None = None


def get_api_key() -> str:
    """APIキーを取得（キャッシュあり）.

    取得優先順位:
    1. 環境変数 JRAVAN_API_KEY
    2. boto3 で API Gateway から動的取得

    Returns:
        APIキー文字列。取得できない場合は空文字列。
    """
    global _cached_api_key
    if _cached_api_key is not None:
        return _cached_api_key

    # 環境変数から取得
    if JRAVAN_API_KEY:
        _cached_api_key = JRAVAN_API_KEY
        logger.info("API key loaded from environment variable")
        return _cached_api_key

    # boto3でAPI Gatewayから取得
    try:
        client = boto3.client("apigateway", region_name="ap-northeast-1")
        response = client.get_api_key(apiKey=JRAVAN_API_KEY_ID, includeValue=True)
        _cached_api_key = response.get("value", "")
        logger.info("API key loaded from API Gateway")
        return _cached_api_key
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error("Failed to get API key from API Gateway: %s - %s", error_code, e)
        _cached_api_key = ""
        return _cached_api_key


def get_headers() -> dict:
    """APIリクエスト用ヘッダーを取得.

    Returns:
        ヘッダー辞書。API Keyがある場合は x-api-key を含む。
    """
    headers = {}
    api_key = get_api_key()
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def get_api_url() -> str:
    """JRA-VAN API のベースURLを取得.

    Returns:
        API ベースURL
    """
    return JRAVAN_API_URL
