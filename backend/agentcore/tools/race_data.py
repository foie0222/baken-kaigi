"""レースデータ取得ツール.

JRA-VAN API を呼び出してレース・馬データを取得する。
"""

import requests
from strands import tool

from .jravan_client import cached_get, get_api_url

VENUE_CODE_TO_NAME: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}


def venue_code_to_name(code: str) -> str:
    """競馬場コード（例: "05"）を名前（例: "東京"）に変換する."""
    return VENUE_CODE_TO_NAME.get(code, code)


def _fetch_race_detail(race_id: str) -> dict:
    """JRA-VAN APIからレース詳細を取得する共通関数."""
    response = cached_get(
        f"{get_api_url()}/races/{race_id}",
    )
    response.raise_for_status()
    data = response.json()
    race = data.get("race")
    if race and "venue" in race:
        race["venue"] = venue_code_to_name(race["venue"])
    return data


def _extract_race_conditions(race: dict) -> list[str]:
    """レース情報からrace_conditions文字列リストを抽出する."""
    conditions = []
    grade_class = race.get("grade_class", "")
    if grade_class:
        grade_lower = grade_class.lower().replace("-", "").replace(" ", "")
        if grade_lower in ("g1", "gi"):
            conditions.append("g1")
        elif grade_lower in ("g2", "gii"):
            conditions.append("g2")
        elif grade_lower in ("g3", "giii"):
            conditions.append("g3")

    age_condition = race.get("age_condition", "")
    if age_condition:
        age_lower = age_condition.lower()
        if "新馬" in age_lower:
            conditions.append("maiden_new")
        elif "未勝利" in age_lower:
            conditions.append("maiden")

    race_name = race.get("race_name", "")
    if "ハンデ" in race_name:
        conditions.append("handicap")
    if "牝" in race_name:
        conditions.append("fillies_mares")

    if race.get("is_obstacle"):
        conditions.append("hurdle")

    return conditions


@tool
def get_race_runners(race_id: str) -> dict:
    """レースの出走馬データを分析ツール向けに取得する。

    他の分析ツール（analyze_bet_selection, analyze_race_characteristics,
    analyze_risk_factors等）に渡すためのデータを整形して返します。
    必ず最初にこのツールを呼んで、返却値を分析ツールの引数に渡してください。

    Args:
        race_id: レースID (例: "202601250611")

    Returns:
        dict:
            - runners_data: 出走馬リスト（horse_number, horse_name, odds, popularity,
              jockey_name, waku_ban）
            - race_conditions: レース条件リスト（"handicap", "maiden_new"等）
            - venue: 競馬場名
            - surface: 馬場（"芝" or "ダート"）
            - distance: 距離
            - total_runners: 出走頭数
            - race_name: レース名
            - error: エラー時のみ
    """
    try:
        data = _fetch_race_detail(race_id)
        race = data.get("race", {})
        runners = data.get("runners", [])

        race_conditions = _extract_race_conditions(race)

        return {
            "runners_data": runners,
            "race_conditions": race_conditions,
            "venue": race.get("venue", ""),
            "surface": race.get("track_type", ""),
            "distance": race.get("distance", 0),
            "total_runners": race.get("horse_count", len(runners)),
            "race_name": race.get("race_name", ""),
        }
    except requests.RequestException as e:
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
