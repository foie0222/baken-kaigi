"""レースデータ取得ツール.

JRA-VAN API を呼び出してレース・馬データを取得する。
"""

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers


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
            f"{get_api_url()}/races/{race_id}",
            headers=get_headers(),
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
            f"{get_api_url()}/races/{race_id}",
            headers=get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
