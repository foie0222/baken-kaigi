"""レースデータ取得ツール.

DynamoDB からレース・馬データを取得する。
"""

import logging

from strands import tool

from . import dynamodb_client

logger = logging.getLogger(__name__)


def _fetch_race_detail(race_id: str) -> dict:
    """DynamoDBからレース詳細を取得する共通関数."""
    race = dynamodb_client.get_race(race_id)
    runners = dynamodb_client.get_runners(race_id)
    return {"race": race or {}, "runners": runners}


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
        data = _fetch_race_detail(race_id)
        return {
            "race": data.get("race", {}),
            "runners": data.get("runners", []),
        }
    except Exception as e:
        return {"error": f"データ取得に失敗しました: {str(e)}"}


@tool
def get_race_runners(race_id: str) -> dict:
    """レースの出走馬データを分析ツール向けに取得する。

    他の分析ツール（analyze_bet_selection, analyze_race_characteristics,
    analyze_risk_factors等）に渡すためのデータを整形して返します。
    必ず最初にこのツールを呼んで、返却値を分析ツールの引数に渡してください。

    Args:
        race_id: レースID (例: "20260125_06_11")

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
    except Exception as e:
        return {"error": f"データ取得に失敗しました: {str(e)}"}
