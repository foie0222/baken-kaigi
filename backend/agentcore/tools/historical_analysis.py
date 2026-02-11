"""過去データ分析ツール.

同コース・同距離・同クラスの過去レース統計を分析する。
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from strands import tool

from .jravan_client import cached_get, get_api_url

logger = logging.getLogger(__name__)

# 並列API呼び出しの最大ワーカー数
MAX_PARALLEL_WORKERS = 5


def _fetch_parallel_stats(api_calls: list[dict]) -> list[dict]:
    """複数のAPI呼び出しを並列実行する.

    Args:
        api_calls: API呼び出し情報のリスト
            各要素は {"url": str, "params": dict} の形式

    Returns:
        各API呼び出しの結果リスト（同じ順序）
    """
    results: list[dict | None] = [None] * len(api_calls)

    def fetch_single(index: int, call: dict) -> tuple[int, dict[str, Any]]:
        try:
            response = cached_get(
                call["url"],
                params=call.get("params", {}),
                timeout=call.get("timeout", API_TIMEOUT_SECONDS),
            )
            if response.status_code == 404:
                return index, {"error": "not_found"}
            response.raise_for_status()
            return index, response.json()
        except requests.RequestException as e:
            logger.error(f"Parallel API call failed: {e}")
            return index, {"error": str(e)}

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        futures = [
            executor.submit(fetch_single, i, call)
            for i, call in enumerate(api_calls)
        ]
        for future in as_completed(futures):
            index, result = future.result()
            results[index] = result

    return [r if r is not None else {"error": "unknown"} for r in results]

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

        response = cached_get(
            f"{get_api_url()}/statistics/past-races",
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


# 騎手成績評価の閾値
JOCKEY_GOOD_WIN_RATE_THRESHOLD = 25  # 好成績と判定する勝率
JOCKEY_POOR_WIN_RATE_THRESHOLD = 10  # 苦手と判定する勝率

# 回収率評価の閾値
ROI_GOOD_THRESHOLD = 90  # 良好と判定する回収率
ROI_POOR_THRESHOLD = 60  # 低いと判定する回収率

# 競馬場コード → 名前のマッピング
VENUE_NAME_TO_CODE = {
    "札幌": "01", "函館": "02", "福島": "03", "新潟": "04",
    "東京": "05", "中山": "06", "中京": "07", "京都": "08",
    "阪神": "09", "小倉": "10",
}


@tool
def analyze_jockey_course_stats(
    jockey_id: str,
    jockey_name: str,
    track_type: str,
    distance: int,
    venue: str | None = None,
) -> dict:
    """騎手の特定コースでの成績を分析する。

    指定された騎手が特定のコース（トラック種別・距離・競馬場）で
    どの程度の成績を残しているかを分析します。

    Args:
        jockey_id: 騎手コード
        jockey_name: 騎手名（表示用）
        track_type: トラック種別（芝、ダート、障害）
        distance: 距離（メートル）
        venue: 競馬場名（省略可、例: "阪神"、"東京"）

    Returns:
        分析結果（成績、評価、コメント）
    """
    try:
        # トラック種別をコードに変換
        track_code = _to_track_code(track_type)

        # 競馬場名をコードに変換
        keibajo_code = VENUE_NAME_TO_CODE.get(venue) if venue else None

        params = {
            "jockey_id": jockey_id,
            "track_code": track_code,
            "distance": distance,
            "limit": DEFAULT_PAST_RACES_LIMIT,
        }
        if keibajo_code:
            params["keibajo_code"] = keibajo_code

        response = cached_get(
            f"{get_api_url()}/statistics/jockey-course",
            params=params,
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "warning": "騎手成績データが見つかりませんでした",
                "jockey_name": jockey_name,
                "conditions": {
                    "track_type": track_type,
                    "distance": distance,
                    "venue": venue,
                },
            }

        response.raise_for_status()
        stats = response.json()

        # 成績評価
        win_rate = stats.get("win_rate", 0)
        assessment = _assess_jockey_performance(win_rate)

        # コメント生成
        venue_text = f"{venue}" if venue else "全場"
        comment = _generate_jockey_comment(
            jockey_name, venue_text, track_type, distance,
            win_rate, stats.get("place_rate", 0), assessment
        )

        return {
            "jockey_name": jockey_name,
            "total_rides": stats.get("total_rides", 0),
            "wins": stats.get("wins", 0),
            "places": stats.get("places", 0),
            "win_rate": f"{win_rate:.1f}%",
            "place_rate": f"{stats.get('place_rate', 0):.1f}%",
            "assessment": assessment,
            "comment": comment,
            "conditions": {
                "track_type": track_type,
                "distance": distance,
                "venue": venue,
            },
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze jockey course stats: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze jockey course stats: {e}")
        return {"error": str(e)}


def _assess_jockey_performance(win_rate: float) -> str:
    """騎手の成績を評価する."""
    if win_rate >= JOCKEY_GOOD_WIN_RATE_THRESHOLD:
        return "好成績"
    elif win_rate < JOCKEY_POOR_WIN_RATE_THRESHOLD:
        return "苦手"
    else:
        return "標準"


def _generate_jockey_comment(
    jockey_name: str,
    venue: str,
    track_type: str,
    distance: int,
    win_rate: float,
    place_rate: float,
    assessment: str,
) -> str:
    """騎手成績のコメントを生成する."""
    base = f"{jockey_name}騎手は{venue}{track_type}{distance}mで"
    if assessment == "好成績":
        return f"{base}勝率{win_rate:.1f}%と好成績を残しています。信頼度が高いです。"
    elif assessment == "苦手":
        return f"{base}勝率{win_rate:.1f}%とやや苦戦傾向にあります。"
    else:
        return f"{base}勝率{win_rate:.1f}%、複勝率{place_rate:.1f}%と標準的な成績です。"


@tool
def analyze_bet_roi(
    track_type: str,
    distance: int,
    popularity: int,
) -> dict:
    """特定人気の買い目回収率を分析する。

    指定された人気順位の馬を買い続けた場合の期待回収率を分析します。
    単勝・複勝それぞれの回収率を算出します。

    Args:
        track_type: トラック種別（芝、ダート、障害）
        distance: 距離（メートル）
        popularity: 人気順（1-18）

    Returns:
        分析結果（回収率、推奨コメント）
    """
    try:
        # トラック種別をコードに変換
        track_code = _to_track_code(track_type)

        response = cached_get(
            f"{get_api_url()}/statistics/popularity-payout",
            params={
                "track_code": track_code,
                "distance": distance,
                "popularity": popularity,
                "limit": DEFAULT_PAST_RACES_LIMIT,
            },
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "warning": "配当統計データが見つかりませんでした",
                "conditions": {
                    "track_type": track_type,
                    "distance": distance,
                    "popularity": popularity,
                },
            }

        response.raise_for_status()
        stats = response.json()

        win_roi = stats.get("estimated_roi_win", 0)
        place_roi = stats.get("estimated_roi_place", 0)

        # 推奨コメント生成
        recommendation = _generate_roi_recommendation(win_roi, place_roi, popularity)

        return {
            "popularity": popularity,
            "total_races": stats.get("total_races", 0),
            "win_roi": f"{win_roi:.1f}%",
            "place_roi": f"{place_roi:.1f}%",
            "avg_win_payout": stats.get("avg_win_payout"),
            "avg_place_payout": stats.get("avg_place_payout"),
            "recommendation": recommendation,
            "conditions": {
                "track_type": track_type,
                "distance": distance,
            },
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze bet ROI: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze bet ROI: {e}")
        return {"error": str(e)}


def _generate_roi_recommendation(win_roi: float, place_roi: float, popularity: int) -> str:
    """回収率に基づく推奨コメントを生成する."""
    better_roi = max(win_roi, place_roi)

    if better_roi >= ROI_GOOD_THRESHOLD:
        if place_roi > win_roi:
            return f"{popularity}番人気の複勝は回収率{place_roi:.1f}%と良好。期待値プラスの可能性があります。"
        else:
            return f"{popularity}番人気の単勝は回収率{win_roi:.1f}%と良好。狙い目です。"
    elif better_roi < ROI_POOR_THRESHOLD:
        return f"{popularity}番人気は単勝{win_roi:.1f}%・複勝{place_roi:.1f}%と回収率が低め。長期的には厳しい傾向です。"
    else:
        if place_roi > win_roi:
            return f"単勝より複勝（{place_roi:.1f}%）の方が回収率は高め。堅実に行くなら複勝がおすすめです。"
        else:
            return f"回収率は単勝{win_roi:.1f}%・複勝{place_roi:.1f}%で標準的。他の要素も考慮して判断してください。"
