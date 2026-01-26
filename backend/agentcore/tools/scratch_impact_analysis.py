"""出走取消・除外馬影響分析ツール.

出走取消や競走除外があった場合の影響を分析する。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30


@tool
def analyze_scratch_impact(
    race_id: str,
    scratched_horses: list[dict] | None = None,
) -> dict:
    """出走取消・除外馬の影響を分析する。

    出走取消や競走除外があった場合、
    残りの馬へのレース展開や人気への影響を分析する。

    Args:
        race_id: 対象レースID
        scratched_horses: 取消/除外馬リスト [{"horse_number": 1, "horse_name": "XX", "reason": "取消"}]
                         Noneの場合はAPIから取得

    Returns:
        取消影響分析結果（展開変化、枠順影響、人気変動予測）
    """
    try:
        # レース情報取得
        race_info = _get_race_info(race_id)
        if "error" in race_info:
            return race_info

        # 出走馬情報取得
        runners = _get_runners(race_id)
        if not runners:
            return {
                "warning": "出走馬情報が取得できませんでした",
                "race_id": race_id,
            }

        # 取消馬情報がない場合はダミーを返す
        if not scratched_horses:
            return {
                "race_id": race_id,
                "has_scratches": False,
                "scratched_count": 0,
                "comment": "出走取消・除外馬なし",
            }

        # 取消馬の影響分析
        scratched_impact = _analyze_scratched_horses(scratched_horses, runners)

        # 展開変化予測
        pace_impact = _predict_pace_impact(scratched_horses, runners)

        # 枠順影響
        gate_impact = _analyze_gate_impact(scratched_horses, runners)

        # 人気変動予測
        popularity_shift = _predict_popularity_shift(scratched_horses, runners)

        # 返還金影響
        refund_impact = _analyze_refund_impact(scratched_horses)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            scratched_horses, scratched_impact, pace_impact, gate_impact
        )

        return {
            "race_id": race_id,
            "has_scratches": True,
            "scratched_count": len(scratched_horses),
            "scratched_horses": scratched_impact,
            "pace_impact": pace_impact,
            "gate_impact": gate_impact,
            "popularity_shift": popularity_shift,
            "refund_impact": refund_impact,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze scratch impact: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze scratch impact: {e}")
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


def _get_runners(race_id: str) -> list[dict]:
    """出走馬情報を取得する."""
    try:
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/runners",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException as e:
        logger.error(f"Failed to get runners: {e}")
        return []


def _analyze_scratched_horses(scratched_horses: list[dict], runners: list[dict]) -> list[dict]:
    """取消馬の影響を分析する."""
    impact_list = []

    for scratched in scratched_horses:
        horse_number = scratched.get("horse_number")
        horse_name = scratched.get("horse_name", "不明")
        reason = scratched.get("reason", "取消")

        # 該当馬を検索
        matching_runner = next(
            (r for r in runners if r.get("horse_number") == horse_number),
            None
        )

        if matching_runner:
            popularity = matching_runner.get("popularity", 0)
            odds = matching_runner.get("odds", "")

            # 人気度による影響判定
            if popularity <= 3:
                impact_level = "大"
                impact_comment = f"{popularity}番人気取消で大きな影響"
            elif popularity <= 6:
                impact_level = "中"
                impact_comment = f"中位人気取消でやや影響"
            else:
                impact_level = "小"
                impact_comment = f"下位人気取消で影響小"
        else:
            popularity = None
            odds = None
            impact_level = "不明"
            impact_comment = "詳細情報なし"

        impact_list.append({
            "horse_number": horse_number,
            "horse_name": horse_name,
            "reason": reason,
            "popularity": popularity,
            "odds": odds,
            "impact_level": impact_level,
            "impact_comment": impact_comment,
        })

    return impact_list


def _predict_pace_impact(scratched_horses: list[dict], runners: list[dict]) -> dict:
    """展開への影響を予測する."""
    # 逃げ馬・先行馬が取消になった場合の影響
    # 簡易版：人気馬取消でペースが緩む可能性

    high_popularity_scratched = any(
        s.get("popularity", 99) <= 3
        for s in scratched_horses
    )

    if high_popularity_scratched:
        return {
            "pace_change": "緩む可能性",
            "reason": "上位人気馬取消でペースが緩む可能性",
            "recommended_style": "差し馬に展開向く可能性",
        }
    else:
        return {
            "pace_change": "影響小",
            "reason": "下位人気取消のため展開への影響は限定的",
            "recommended_style": "大きな変化なし",
        }


def _analyze_gate_impact(scratched_horses: list[dict], runners: list[dict]) -> dict:
    """枠順への影響を分析する."""
    scratched_numbers = [s.get("horse_number", 0) for s in scratched_horses]

    # 内枠取消
    inner_scratched = [n for n in scratched_numbers if n and n <= 4]
    # 外枠取消
    outer_scratched = [n for n in scratched_numbers if n and n >= 13]

    if inner_scratched:
        inner_impact = "内枠スペース空く"
    else:
        inner_impact = "影響なし"

    if outer_scratched:
        outer_impact = "外枠スペース空く"
    else:
        outer_impact = "影響なし"

    return {
        "inner_gate_impact": inner_impact,
        "outer_gate_impact": outer_impact,
        "scratched_positions": scratched_numbers,
        "comment": _generate_gate_comment(inner_scratched, outer_scratched),
    }


def _generate_gate_comment(inner_scratched: list, outer_scratched: list) -> str:
    """枠順コメントを生成する."""
    if inner_scratched and outer_scratched:
        return "内外両方に取消あり、馬群が散る可能性"
    elif inner_scratched:
        return "内枠取消で内側にスペース"
    elif outer_scratched:
        return "外枠取消で外側にスペース"
    else:
        return "枠順への大きな影響なし"


def _predict_popularity_shift(scratched_horses: list[dict], runners: list[dict]) -> dict:
    """人気変動を予測する."""
    # 上位人気取消の場合、次位以降の人気が繰り上がる

    scratched_popularities = [
        s.get("popularity", 99)
        for s in scratched_horses
        if s.get("popularity")
    ]

    if not scratched_popularities:
        return {
            "shift_expected": False,
            "comment": "人気変動データなし",
        }

    min_popularity = min(scratched_popularities)

    if min_popularity == 1:
        return {
            "shift_expected": True,
            "shift_level": "大",
            "comment": "1番人気取消で大きな人気変動予想",
            "new_favorite": "2番人気が繰り上がり",
        }
    elif min_popularity <= 3:
        return {
            "shift_expected": True,
            "shift_level": "中",
            "comment": f"{min_popularity}番人気取消で人気変動あり",
            "new_favorite": "上位人気に変動",
        }
    else:
        return {
            "shift_expected": False,
            "shift_level": "小",
            "comment": "下位人気取消のため大きな変動なし",
        }


def _analyze_refund_impact(scratched_horses: list[dict]) -> dict:
    """返還金への影響を分析する."""
    count = len(scratched_horses)

    if count == 0:
        return {
            "refund_expected": False,
            "comment": "取消なし",
        }

    # 取消馬番
    horse_numbers = [s.get("horse_number", 0) for s in scratched_horses]

    return {
        "refund_expected": True,
        "scratched_numbers": horse_numbers,
        "affected_bets": [
            "単勝",
            "複勝",
            "枠連（該当枠）",
            "馬連",
            "馬単",
            "ワイド",
            "三連複",
            "三連単",
        ],
        "comment": f"馬番{', '.join(map(str, horse_numbers))}絡みの馬券は返還対象",
    }


def _generate_overall_comment(
    scratched_horses: list[dict],
    scratched_impact: list[dict],
    pace_impact: dict,
    gate_impact: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    count = len(scratched_horses)
    parts.append(f"出走取消{count}頭")

    # 大きな影響があった馬
    major_impacts = [s for s in scratched_impact if s.get("impact_level") == "大"]
    if major_impacts:
        names = [s.get("horse_name", "") for s in major_impacts]
        parts.append(f"{'、'.join(names)}の取消が大きな影響")

    # 展開影響
    pace_change = pace_impact.get("pace_change", "")
    if pace_change != "影響小":
        parts.append(pace_change)

    # 枠順影響
    gate_comment = gate_impact.get("comment", "")
    if gate_comment and "影響なし" not in gate_comment:
        parts.append(gate_comment)

    return "。".join(parts) + "。"
