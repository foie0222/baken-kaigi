"""レースデータ取得ツール.

JRA-VAN API を呼び出してレース・馬データを取得する。
"""

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers


@tool
def get_race_data(race_id: str) -> dict:
    """レース情報と出走馬一覧を一括取得する。

    1回のAPI呼び出しでレースの基本情報と出走馬一覧を同時に取得します。
    get_race_info と get_race_runners の機能を統合しています。

    Args:
        race_id: レースID (例: "20260125_06_11")

    Returns:
        race: レース情報（レース名、開催場、距離、馬場状態など）
        runners: 出走馬情報のリスト（馬番、馬名、騎手、オッズ、人気）
    """
    try:
        response = requests.get(
            f"{get_api_url()}/races/{race_id}",
            headers=get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "race": data.get("race", {}),
            "runners": data.get("runners", []),
        }
    except requests.RequestException as e:
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
