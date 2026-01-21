"""レースデータ取得ツール.

JRA-VAN API を呼び出してレース・馬データを取得する。
"""

import os

import requests
from strands import tool

JRAVAN_API_URL = os.environ.get(
    "JRAVAN_API_URL",
    "https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod",
)


@tool
def get_race_runners(race_id: str) -> dict:
    """指定されたレースの出走馬一覧を取得する。

    Args:
        race_id: レースID (例: "202506050811")

    Returns:
        出走馬情報のリスト（馬番、馬名、騎手、オッズ、人気）
    """
    try:
        response = requests.get(
            f"{JRAVAN_API_URL}/races/{race_id}/runners",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
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
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
