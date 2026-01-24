"""過去データ分析ツール.

同コース・同距離・同クラスの過去レース統計を分析する。
"""

import logging
import os

import requests
from strands import tool

logger = logging.getLogger(__name__)

JRAVAN_API_URL = os.environ.get(
    "JRAVAN_API_URL",
    "https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod",
)

# 定数定義
DEFAULT_PAST_RACES_LIMIT = 100  # 集計対象レース数のデフォルト値
API_TIMEOUT_SECONDS = 30  # API呼び出しのタイムアウト秒数
TOP_POPULARITY_DISPLAY_COUNT = 5  # 表示する人気順位の上限
SOLID_RACE_WIN_RATE_THRESHOLD = 35  # 堅いレースと判定する1番人気勝率の閾値
UPSET_RACE_WIN_RATE_THRESHOLD = 20  # 荒れやすいレースと判定する1番人気勝率の閾値


@tool
def analyze_past_race_trends(
    race_id: str,
    track_type: str,
    distance: int,
    grade_class: str,
) -> dict:
    """過去レース統計を分析し、傾向を提示する。

    同コース・同距離・同クラスの過去統計から、人気別勝率や
    配当傾向を分析します。

    Args:
        race_id: レースID
        track_type: トラック種別（芝、ダート、障害）
        distance: 距離（メートル）
        grade_class: クラス（新馬、未勝利、1勝、G3など）

    Returns:
        分析結果（人気別傾向、荒れやすさなど）
    """
    try:
        # トラック種別をコードに変換
        track_code = _to_track_code(track_type)

        response = requests.get(
            f"{JRAVAN_API_URL}/statistics/past-races",
            params={
                "track_code": track_code,
                "distance": distance,
                "grade_code": grade_class if grade_class else None,
                "limit": DEFAULT_PAST_RACES_LIMIT,
            },
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "warning": "過去統計データが見つかりませんでした",
                "race_id": race_id,
                "conditions": {
                    "track_type": track_type,
                    "distance": distance,
                    "grade_class": grade_class,
                },
            }

        response.raise_for_status()
        stats = response.json()

        # 人気別勝率の分析
        popularity_stats = stats.get("popularity_stats", [])
        first_pop_stats = next(
            (s for s in popularity_stats if s["popularity"] == 1),
            None
        )

        # レース傾向判定
        tendency = _analyze_race_tendency(first_pop_stats)

        return {
            "race_id": race_id,
            "total_races_analyzed": stats.get("total_races", 0),
            "conditions": {
                "track_type": track_type,
                "distance": distance,
                "grade_class": grade_class,
            },
            "first_popularity": {
                "win_rate": f"{first_pop_stats['win_rate']:.1f}%" if first_pop_stats else "データなし",
                "place_rate": f"{first_pop_stats['place_rate']:.1f}%" if first_pop_stats else "データなし",
            },
            "race_tendency": tendency,
            "popularity_trends": [
                {
                    "popularity": stat["popularity"],
                    "win_rate": f"{stat['win_rate']:.1f}%",
                    "place_rate": f"{stat['place_rate']:.1f}%",
                    "sample_size": stat["total_runs"],
                }
                for stat in popularity_stats[:TOP_POPULARITY_DISPLAY_COUNT]
            ],
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze past trends: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze past trends: {e}")
        return {"error": str(e)}


def _to_track_code(track_type: str) -> str:
    """トラック種別をAPIのtrack_codeに変換する."""
    track_map = {
        "芝": "1",
        "ダート": "2",
        "ダ": "2",
        "障害": "3",
    }
    return track_map.get(track_type, "1")


def _analyze_race_tendency(first_pop_stats: dict | None) -> str:
    """レース傾向を判定（堅い/標準/荒れやすい）."""
    if not first_pop_stats:
        return "データ不足"

    win_rate = first_pop_stats.get("win_rate", 0)

    # 1番人気勝率で判定
    if win_rate >= SOLID_RACE_WIN_RATE_THRESHOLD:
        return "堅いレース（1番人気が好走しやすい）"
    elif win_rate <= UPSET_RACE_WIN_RATE_THRESHOLD:
        return "荒れやすいレース（人気薄が好走しやすい）"
    else:
        return "標準的なレース"
