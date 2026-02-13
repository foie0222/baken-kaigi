"""予想的中率分析ツール.

過去の予想データを分析し、様々な条件下での的中率を算出する。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30


@tool
def analyze_bet_probability(
    race_id: str,
    bet_type: str = "単勝",
    analysis_scope: str = "条件別",
) -> dict:
    """予想的中率を分析し、賭け方の傾向を判断する。

    指定されたレースと賭け方に対して、過去の的中率統計を分析し、
    どのような条件下で的中しやすいかを示す。

    Args:
        race_id: 対象レースID
        bet_type: 賭け種別（単勝/複勝/馬連/馬単/三連複/三連単）
        analysis_scope: 分析範囲（条件別/人気別/オッズ帯別）

    Returns:
        的中率分析結果（条件別的中率、推奨賭け方、期待値など）
    """
    try:
        # レース情報取得
        race_info = _get_race_info(race_id)
        if "error" in race_info:
            return race_info

        # 過去の統計情報を取得
        stats = _get_past_statistics(race_info, bet_type)
        if stats is None:
            return {
                "warning": "統計データが見つかりませんでした",
                "race_id": race_id,
            }

        # 的中率分析
        probability_analysis = _analyze_probability(stats, analysis_scope)

        # 期待値計算
        expected_value = _calculate_expected_value(stats, bet_type)

        # 推奨判断
        recommendation = _generate_recommendation(probability_analysis, expected_value)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            bet_type, probability_analysis, expected_value, recommendation
        )

        return {
            "race_id": race_id,
            "bet_type": bet_type,
            "analysis_scope": analysis_scope,
            "probability_analysis": probability_analysis,
            "expected_value": expected_value,
            "recommendation": recommendation,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze bet probability: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze bet probability: {e}")
        return {"error": str(e)}


def _get_race_info(race_id: str) -> dict:
    """レース基本情報を取得する."""
    try:
        response = requests.get(
            f"{get_api_url()}/races/{race_id}",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return {"error": "レース情報が見つかりませんでした", "race_id": race_id}
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get race info: {e}")
        return {"error": f"レース情報取得エラー: {str(e)}"}


def _get_past_statistics(race_info: dict, bet_type: str) -> dict | None:
    """過去の統計情報を取得する."""
    try:
        track_code = {"芝": "1", "ダート": "2", "障害": "3"}.get(
            race_info.get("track_type", "芝"), "1"
        )
        response = requests.get(
            f"{get_api_url()}/statistics/past-races",
            params={
                "track_code": track_code,
                "distance": race_info.get("distance", 1600),
                "limit": 100,
            },
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        logger.error(f"Failed to get past statistics: {e}")
        return None


def _analyze_probability(stats: dict, scope: str) -> dict:
    """的中率を分析する."""
    popularity_stats = stats.get("popularity_stats", [])

    if scope == "人気別":
        # 人気別的中率
        by_popularity = []
        for ps in popularity_stats[:5]:  # 上位5人気
            by_popularity.append({
                "popularity": ps["popularity"],
                "win_rate": ps["win_rate"],
                "place_rate": ps["place_rate"],
            })
        return {
            "type": "人気別",
            "data": by_popularity,
            "summary": _summarize_popularity_stats(by_popularity),
        }

    elif scope == "オッズ帯別":
        # オッズ帯別的中率（人気から推定）
        odds_ranges = [
            {"range": "1.0-2.0倍", "popularity": [1], "label": "圧倒的人気"},
            {"range": "2.1-5.0倍", "popularity": [1, 2], "label": "上位人気"},
            {"range": "5.1-10.0倍", "popularity": [2, 3, 4], "label": "中位人気"},
            {"range": "10.1-30.0倍", "popularity": [4, 5, 6], "label": "中穴"},
            {"range": "30.1倍以上", "popularity": [7, 8, 9, 10], "label": "大穴"},
        ]
        by_odds = []
        for odds_range in odds_ranges:
            relevant_stats = [
                ps for ps in popularity_stats
                if ps["popularity"] in odds_range["popularity"]
            ]
            if relevant_stats:
                avg_win = sum(s["win_rate"] for s in relevant_stats) / len(relevant_stats)
                avg_place = sum(s["place_rate"] for s in relevant_stats) / len(relevant_stats)
            else:
                avg_win = 0.0
                avg_place = 0.0
            by_odds.append({
                "odds_range": odds_range["range"],
                "label": odds_range["label"],
                "win_rate": round(avg_win, 1),
                "place_rate": round(avg_place, 1),
            })
        return {
            "type": "オッズ帯別",
            "data": by_odds,
            "summary": _summarize_odds_stats(by_odds),
        }

    else:  # 条件別
        # 条件別分析（総合）
        total_races = stats.get("total_races", 0)
        favorite_win = 0.0
        top3_place = 0.0

        if popularity_stats:
            favorite = next((ps for ps in popularity_stats if ps["popularity"] == 1), None)
            if favorite:
                favorite_win = favorite["win_rate"]
            top3 = [ps for ps in popularity_stats if ps["popularity"] <= 3]
            if top3:
                # 上位3人気の平均複勝率は、実際に存在する件数で割る
                top3_place = sum(ps["place_rate"] for ps in top3) / len(top3)

        return {
            "type": "条件別",
            "total_races": total_races,
            "favorite_win_rate": favorite_win,
            "top3_place_rate": round(top3_place, 1),
            "summary": f"1番人気勝率{favorite_win}%、上位3人気平均複勝率{round(top3_place, 1)}%",
        }


def _summarize_popularity_stats(by_popularity: list) -> str:
    """人気別統計をサマリーする."""
    if not by_popularity:
        return "データ不足"

    best = max(by_popularity, key=lambda x: x["win_rate"])
    return f"{best['popularity']}番人気が最も勝率高く{best['win_rate']}%"


def _summarize_odds_stats(by_odds: list) -> str:
    """オッズ帯別統計をサマリーする."""
    if not by_odds:
        return "データ不足"

    # 期待値的に優れているオッズ帯を判定（簡易版）
    return "上位人気が安定、中穴も狙い目"


def _calculate_expected_value(stats: dict, bet_type: str) -> dict:
    """期待値を計算する."""
    avg_win_payout = stats.get("avg_win_payout", 0) or 0
    avg_place_payout = stats.get("avg_place_payout", 0) or 0
    popularity_stats = stats.get("popularity_stats", [])

    if bet_type == "単勝":
        # 単勝期待値（1番人気基準）
        favorite = next((ps for ps in popularity_stats if ps["popularity"] == 1), None)
        if favorite:
            ev = (favorite["win_rate"] / 100) * avg_win_payout if avg_win_payout else 0
            return {
                "bet_type": "単勝",
                "expected_return": round(ev, 0),
                "comment": "期待値" + ("プラス" if ev > 100 else "マイナス"),
            }

    elif bet_type == "複勝":
        # 複勝期待値
        favorite = next((ps for ps in popularity_stats if ps["popularity"] == 1), None)
        if favorite:
            ev = (favorite["place_rate"] / 100) * avg_place_payout if avg_place_payout else 0
            return {
                "bet_type": "複勝",
                "expected_return": round(ev, 0),
                "comment": "期待値" + ("プラス" if ev > 100 else "マイナス"),
            }

    return {
        "bet_type": bet_type,
        "expected_return": 0,
        "comment": "計算データ不足",
    }


def _generate_recommendation(probability_analysis: dict, expected_value: dict) -> dict:
    """推奨を生成する."""
    ev = expected_value.get("expected_return", 0)
    prob_type = probability_analysis.get("type", "")

    if ev > 100:
        confidence = "高"
        action = "積極的に購入を検討"
    elif ev > 80:
        confidence = "中"
        action = "条件次第で購入を検討"
    else:
        confidence = "低"
        action = "控えめに"

    return {
        "confidence": confidence,
        "suggested_action": action,
        "key_factors": [prob_type + "の分析結果を参考に"],
    }


def _generate_overall_comment(
    bet_type: str,
    probability_analysis: dict,
    expected_value: dict,
    recommendation: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # 賭け方の特徴
    parts.append(f"{bet_type}の分析結果")

    # 確率分析結果
    summary = probability_analysis.get("summary", "")
    if summary:
        parts.append(summary)

    # 推奨
    parts.append(recommendation.get("suggested_action", ""))

    return "。".join(parts) + "。"
