"""レースデータ取得ツール.

JRA-VAN API を呼び出してレース・馬データを取得する。
"""

import os

import boto3
import requests
from strands import tool

JRAVAN_API_URL = os.environ.get(
    "JRAVAN_API_URL",
    "https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod",
)
JRAVAN_API_KEY = os.environ.get("JRAVAN_API_KEY", "")
JRAVAN_API_KEY_ID = os.environ.get("JRAVAN_API_KEY_ID", "zeq5hh8qp6")

_cached_api_key: str | None = None


def _get_api_key() -> str:
    """APIキーを取得（キャッシュあり）."""
    global _cached_api_key
    if _cached_api_key is not None:
        return _cached_api_key

    # 環境変数から取得
    if JRAVAN_API_KEY:
        _cached_api_key = JRAVAN_API_KEY
        return _cached_api_key

    # boto3でAPI Gatewayから取得
    try:
        client = boto3.client("apigateway", region_name="ap-northeast-1")
        response = client.get_api_key(apiKey=JRAVAN_API_KEY_ID, includeValue=True)
        _cached_api_key = response.get("value", "")
        return _cached_api_key
    except Exception:
        _cached_api_key = ""
        return _cached_api_key


def _get_headers() -> dict:
    """APIリクエスト用ヘッダーを取得."""
    headers = {}
    api_key = _get_api_key()
    if api_key:
        headers["x-api-key"] = api_key
    return headers


@tool
def get_race_runners(race_id: str) -> dict:
    """指定されたレースの出走馬一覧を取得する。

    Args:
        race_id: レースID (例: "20260125_06_11")

    Returns:
        出走馬情報のリスト（馬番、馬名、騎手、オッズ、人気）
    """
    try:
        response = requests.get(
            f"{JRAVAN_API_URL}/races/{race_id}",
            headers=_get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        # runners フィールドを返す
        return {"runners": data.get("runners", []), "race": data.get("race", {})}
    except requests.RequestException as e:
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}


@tool
def get_race_info(race_id: str) -> dict:
    """指定されたレースの詳細情報を取得する。

    Args:
        race_id: レースID

    Returns:
        レース情報（レース名、開催場、距離、馬場状態など）
    """
    try:
        response = requests.get(
            f"{JRAVAN_API_URL}/races/{race_id}",
            headers=_get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
