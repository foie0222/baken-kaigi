"""相手馬選定ツール.

軸馬に対する相手馬を選定し、買い目の組み立てを支援する。
"""

import logging
from itertools import combinations, permutations

import requests
from strands import tool

from .jravan_client import cached_get, get_api_url

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# スコア閾値
SCORE_HIGH_CONFIDENCE = 75
SCORE_MEDIUM_CONFIDENCE = 60
SCORE_VALUE_PICK = 45
SCORE_EXCLUDE_CRITICAL = 40

# 予算配分比率
HIGH_CONFIDENCE_RATIO = 0.5
MEDIUM_CONFIDENCE_RATIO = 0.3
VALUE_RATIO = 0.2

# オッズ関連
VALUE_PICK_MIN_ODDS = 10
FAVORITE_ODDS_THRESHOLD = 5.0
EXPECTED_ODDS_HIGH = 5.0
EXPECTED_ODDS_MEDIUM = 10.0
EXPECTED_ODDS_LOW = 20.0
ODDS_VALUE_UNDER_RATIO = 0.7
ODDS_VALUE_OVER_RATIO = 1.5

# スコア計算パラメータ
BASE_SCORE = 50
SCORE_DELTA_STYLE = 5
SCORE_DELTA_INNER_GATE = 5
SCORE_DELTA_OUTER_GATE = -5
INNER_GATE_MAX = 4
OUTER_GATE_MIN = 14
MAX_REASONS_DISPLAY = 3

# 過去成績評価パラメータ
FORM_AVG_EXCELLENT = 3.0
FORM_AVG_GOOD = 5.0
FORM_SCORE_EXCELLENT = 20
FORM_SCORE_GOOD = 10
FORM_SCORE_POOR = -10
IN_MONEY_THRESHOLD = 3
PERFORMANCE_LIMIT = 5

# 買い目生成パラメータ
BET_HIGH_RATIO = 0.15
BET_MEDIUM_RATIO = 0.08
BET_VALUE_RATIO = 0.04
ODDS_ESTIMATE_FACTOR = 1.2
DEFAULT_AXIS_ODDS = 5.0
DEFAULT_PARTNER_ODDS = 10.0
MIN_BET_AMOUNT = 100
MAX_PARTNERS_TO_PROCESS = 6
MAX_BET_SUGGESTIONS = 8

# 表示数制限
MAX_HIGH_CONFIDENCE = 3
MAX_MEDIUM_CONFIDENCE = 3
MAX_VALUE_PICKS = 3
MAX_EXCLUDED_HORSES = 5


@tool
def suggest_bet_combinations(
    race_id: str,
    axis_horses: list[int],
    bet_type: str,
    budget: int,
) -> dict:
    """軸馬に対する相手馬を選定し、買い目の組み立てを支援する。

    軸馬に対する相手馬の選定、穴馬の発掘、危険馬の特定、
    買い目の優先度付けを行う。

    Args:
        race_id: レースID (例: "20260125_05_11")
        axis_horses: 軸馬の馬番リスト
        bet_type: 券種 ("馬連", "馬単", "ワイド", "3連複", "3連単")
        budget: 予算（円）

    Returns:
        相手馬選定結果（軸馬情報、相手馬候補、消し馬、買い目提案、予算配分）
    """
    try:
        # 入力検証
        if not axis_horses:
            return {"error": "軸馬が指定されていません", "race_id": race_id}
        if budget <= 0:
            return {"error": "予算は正の数を指定してください", "race_id": race_id}

        # 出走馬リスト取得
        runners = _get_runners(race_id)
        if not runners:
            return {"error": "出走馬データが取得できませんでした", "race_id": race_id}

        # 軸馬の存在確認
        runner_numbers = {r.get("horse_number") for r in runners}
        invalid_axes = [h for h in axis_horses if h not in runner_numbers]
        if invalid_axes:
            return {"error": f"無効な軸馬番号: {invalid_axes}", "race_id": race_id}

        # オッズデータ取得
        odds_data = _get_current_odds(race_id)

        # 脚質データ取得
        running_styles = _get_running_styles(race_id)

        # 各馬のスコアを計算
        horse_scores = _calculate_horse_scores(runners, running_styles)

        # 軸馬情報の抽出
        axis_info = _extract_axis_info(axis_horses, runners, horse_scores)

        # 相手馬候補の選定
        partners = _select_partners(
            axis_horses, runners, horse_scores, odds_data
        )

        # 消し馬の特定
        excluded = _identify_excluded_horses(
            axis_horses, runners, horse_scores, odds_data
        )

        # 買い目提案の生成
        bet_suggestions = _generate_bet_suggestions(
            axis_horses, partners, bet_type, odds_data, budget
        )

        # 予算配分
        budget_allocation = _allocate_budget(budget, partners)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            axis_info, partners, excluded
        )

        return {
            "race_id": race_id,
            "axis_horses": axis_info,
            "suggested_partners": partners,
            "excluded_horses": excluded,
            "bet_suggestions": bet_suggestions,
            "budget_allocation": budget_allocation,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to suggest bet combinations: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to suggest bet combinations: {e}")
        return {"error": str(e)}


def _get_runners(race_id: str) -> list[dict]:
    """出走馬リストを取得する."""
    try:
        response = cached_get(
            f"{get_api_url()}/races/{race_id}/runners",
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("runners", [])
    except requests.RequestException as e:
        logger.error(f"Failed to get runners for race {race_id}: {e}")
        return []


def _get_current_odds(race_id: str) -> dict:
    """現在のオッズを取得する."""
    try:
        response = cached_get(
            f"{get_api_url()}/races/{race_id}/odds/win",
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return {o.get("horse_number"): o.get("odds", 0) for o in data.get("odds", [])}
    except requests.RequestException as e:
        logger.error(f"Failed to get odds for race {race_id}: {e}")
        return {}


def _get_running_styles(race_id: str) -> list[dict]:
    """脚質データを取得する."""
    try:
        response = cached_get(
            f"{get_api_url()}/races/{race_id}/running-styles",
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("running_styles", [])
    except requests.RequestException as e:
        logger.error(f"Failed to get running styles for race {race_id}: {e}")
        return []


def _calculate_horse_scores(
    runners: list[dict],
    running_styles: list[dict],
) -> dict[int, dict]:
    """各馬のスコアと評価理由を計算する."""
    style_map = {r.get("horse_number"): r.get("running_style", "不明") for r in running_styles}
    scores = {}

    for runner in runners:
        horse_number = runner.get("horse_number")
        horse_id = runner.get("horse_id", "")

        # 基本スコアと理由
        score = BASE_SCORE
        reasons = []
        risk_reasons = []

        # 過去成績から評価
        form_score, form_reasons, form_risks = _evaluate_form(horse_id)
        score += form_score
        reasons.extend(form_reasons)
        risk_reasons.extend(form_risks)

        # 脚質評価
        style = style_map.get(horse_number, "不明")
        if style in ["先行", "差し"]:
            score += SCORE_DELTA_STYLE
            reasons.append("脚質良好")
        elif style == "追込":
            risk_reasons.append("追込脚質")

        # 枠順評価
        if horse_number <= INNER_GATE_MAX:
            score += SCORE_DELTA_INNER_GATE
            reasons.append("内枠有利")
        elif horse_number >= OUTER_GATE_MIN:
            score += SCORE_DELTA_OUTER_GATE
            risk_reasons.append("外枠不利")

        scores[horse_number] = {
            "score": min(100, max(0, score)),
            "reasons": reasons[:MAX_REASONS_DISPLAY],
            "risk_reasons": risk_reasons[:MAX_REASONS_DISPLAY],
        }

    return scores


def _evaluate_form(horse_id: str) -> tuple[int, list[str], list[str]]:
    """過去成績から評価する."""
    score_delta = 0
    reasons = []
    risk_reasons = []

    try:
        response = cached_get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": PERFORMANCE_LIMIT},
            timeout=API_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            performances = data.get("performances", [])
            if performances:
                finishes = [p.get("finish_position", 0) for p in performances if p.get("finish_position", 0) > 0]
                if finishes:
                    avg = sum(finishes) / len(finishes)
                    in_money = sum(1 for f in finishes if f <= 3)

                    if avg <= FORM_AVG_EXCELLENT:
                        score_delta += FORM_SCORE_EXCELLENT
                        reasons.append("好成績継続")
                    elif avg <= FORM_AVG_GOOD:
                        score_delta += FORM_SCORE_GOOD
                        reasons.append("安定した成績")
                    else:
                        score_delta += FORM_SCORE_POOR
                        risk_reasons.append("成績不振")

                    if in_money >= IN_MONEY_THRESHOLD:
                        score_delta += SCORE_DELTA_STYLE
                        reasons.append("馬券圏内率高い")
    except requests.RequestException as e:
        logger.debug(f"Failed to get performances for horse {horse_id}: {e}")

    return score_delta, reasons, risk_reasons


def _extract_axis_info(
    axis_horses: list[int],
    runners: list[dict],
    horse_scores: dict[int, dict],
) -> list[dict]:
    """軸馬情報を抽出する."""
    axis_info = []
    runner_map = {r.get("horse_number"): r for r in runners}

    for horse_number in axis_horses:
        runner = runner_map.get(horse_number, {})
        score_info = horse_scores.get(horse_number, {"score": BASE_SCORE})

        confidence = "高" if score_info["score"] >= SCORE_HIGH_CONFIDENCE else "中"
        axis_info.append({
            "number": horse_number,
            "name": runner.get("horse_name", ""),
            "confidence": confidence,
        })

    return axis_info


def _select_partners(
    axis_horses: list[int],
    runners: list[dict],
    horse_scores: dict[int, dict],
    odds_data: dict,
) -> dict:
    """相手馬候補を選定する."""
    high_confidence = []
    medium_confidence = []
    value_picks = []

    runner_map = {r.get("horse_number"): r for r in runners}

    for horse_number, score_info in horse_scores.items():
        if horse_number in axis_horses:
            continue

        runner = runner_map.get(horse_number, {})
        score = score_info["score"]
        reasons = score_info.get("reasons", [])
        odds = odds_data.get(horse_number, 0)

        # オッズ価値判定
        odds_value = _evaluate_odds_value(score, odds)

        partner = {
            "number": horse_number,
            "name": runner.get("horse_name", ""),
            "score": score,
            "reasons": reasons if reasons else ["データ不足"],
            "odds_value": odds_value,
        }

        if score >= SCORE_HIGH_CONFIDENCE:
            high_confidence.append(partner)
        elif score >= SCORE_MEDIUM_CONFIDENCE:
            medium_confidence.append(partner)
        elif score >= SCORE_VALUE_PICK and odds >= VALUE_PICK_MIN_ODDS:
            partner["reasons"].append("オッズ妙味")
            value_picks.append(partner)

    # スコア順にソート
    high_confidence.sort(key=lambda x: x["score"], reverse=True)
    medium_confidence.sort(key=lambda x: x["score"], reverse=True)
    value_picks.sort(key=lambda x: x["score"], reverse=True)

    return {
        "high_confidence": high_confidence[:MAX_HIGH_CONFIDENCE],
        "medium_confidence": medium_confidence[:MAX_MEDIUM_CONFIDENCE],
        "value_picks": value_picks[:MAX_VALUE_PICKS],
    }


def _evaluate_odds_value(score: int, odds: float) -> str:
    """オッズの価値を評価する."""
    if odds <= 0:
        return "データなし"

    # スコアに対する期待オッズ
    if score >= SCORE_HIGH_CONFIDENCE:
        expected_odds = EXPECTED_ODDS_HIGH
    elif score >= SCORE_MEDIUM_CONFIDENCE:
        expected_odds = EXPECTED_ODDS_MEDIUM
    else:
        expected_odds = EXPECTED_ODDS_LOW

    if odds < expected_odds * ODDS_VALUE_UNDER_RATIO:
        return "過剰人気"
    elif odds > expected_odds * ODDS_VALUE_OVER_RATIO:
        return "お値打ち"
    else:
        return "適正"


def _identify_excluded_horses(
    axis_horses: list[int],
    runners: list[dict],
    horse_scores: dict[int, dict],
    odds_data: dict,
) -> list[dict]:
    """消し馬を特定する."""
    excluded = []
    runner_map = {r.get("horse_number"): r for r in runners}

    for horse_number, score_info in horse_scores.items():
        if horse_number in axis_horses:
            continue

        score = score_info["score"]
        risk_reasons = score_info.get("risk_reasons", [])
        odds = odds_data.get(horse_number, 0)

        # 消し条件: スコアが低い または 人気なのにスコアが低い
        if score < SCORE_VALUE_PICK or (odds > 0 and odds <= FAVORITE_ODDS_THRESHOLD and score < SCORE_MEDIUM_CONFIDENCE):
            runner = runner_map.get(horse_number, {})

            if not risk_reasons:
                risk_reasons = ["総合評価低"]

            risk_level = "消し推奨" if score < SCORE_EXCLUDE_CRITICAL else "注意"

            excluded.append({
                "number": horse_number,
                "name": runner.get("horse_name", ""),
                "reasons": risk_reasons,
                "risk_level": risk_level,
            })

    # スコアが低い順にソート
    excluded.sort(key=lambda x: horse_scores.get(x["number"], {}).get("score", 0))

    return excluded[:MAX_EXCLUDED_HORSES]


def _generate_bet_suggestions(
    axis_horses: list[int],
    partners: dict,
    bet_type: str,
    odds_data: dict,
    budget: int,
) -> list[dict]:
    """買い目提案を生成する."""
    suggestions = []

    # 相手馬を優先度順に取得
    all_partners = (
        partners.get("high_confidence", [])
        + partners.get("medium_confidence", [])
        + partners.get("value_picks", [])
    )

    if bet_type in ["3連複", "3連単"]:
        # 3連系: 軸馬と相手馬2頭の組み合わせ
        processed = all_partners[:MAX_PARTNERS_TO_PROCESS]
        if bet_type == "3連複":
            partner_pairs = combinations(processed, 2)
        else:
            # 3連単は着順があるため順列を使用
            partner_pairs = permutations(processed, 2)
        for p1, p2 in partner_pairs:
            for axis in axis_horses:
                nums = [axis, p1["number"], p2["number"]]
                if bet_type == "3連複":
                    nums_sorted = sorted(nums)
                    combination = f"{nums_sorted[0]}-{nums_sorted[1]}-{nums_sorted[2]}"
                else:
                    combination = f"{axis}-{p1['number']}-{p2['number']}"

                axis_odds = odds_data.get(axis, DEFAULT_AXIS_ODDS)
                p1_odds = odds_data.get(p1["number"], DEFAULT_PARTNER_ODDS)
                p2_odds = odds_data.get(p2["number"], DEFAULT_PARTNER_ODDS)
                estimated_odds = (axis_odds * p1_odds * p2_odds) ** (1 / 3) * ODDS_ESTIMATE_FACTOR

                min_score = min(p1["score"], p2["score"])
                if min_score >= SCORE_HIGH_CONFIDENCE:
                    confidence = "高"
                    amount = int(budget * BET_HIGH_RATIO)
                elif min_score >= SCORE_MEDIUM_CONFIDENCE:
                    confidence = "中"
                    amount = int(budget * BET_MEDIUM_RATIO)
                else:
                    confidence = "低（穴狙い）"
                    amount = int(budget * BET_VALUE_RATIO)

                suggestions.append({
                    "bet_type": bet_type,
                    "combination": combination,
                    "estimated_odds": round(estimated_odds, 1),
                    "confidence": confidence,
                    "suggested_amount": max(MIN_BET_AMOUNT, (amount // MIN_BET_AMOUNT) * MIN_BET_AMOUNT),
                })
    else:
        # 2連系: 軸馬と相手馬1頭の組み合わせ
        for partner in all_partners[:MAX_PARTNERS_TO_PROCESS]:
            for axis in axis_horses:
                if bet_type in ["馬連", "ワイド"]:
                    combination = f"{min(axis, partner['number'])}-{max(axis, partner['number'])}"
                else:
                    combination = f"{axis}-{partner['number']}"

                axis_odds = odds_data.get(axis, DEFAULT_AXIS_ODDS)
                partner_odds = odds_data.get(partner["number"], DEFAULT_PARTNER_ODDS)
                estimated_odds = (axis_odds * partner_odds) ** 0.5 * ODDS_ESTIMATE_FACTOR

                if partner["score"] >= SCORE_HIGH_CONFIDENCE:
                    confidence = "高"
                    amount = int(budget * BET_HIGH_RATIO)
                elif partner["score"] >= SCORE_MEDIUM_CONFIDENCE:
                    confidence = "中"
                    amount = int(budget * BET_MEDIUM_RATIO)
                else:
                    confidence = "低（穴狙い）"
                    amount = int(budget * BET_VALUE_RATIO)

                suggestions.append({
                    "bet_type": bet_type,
                    "combination": combination,
                    "estimated_odds": round(estimated_odds, 1),
                    "confidence": confidence,
                    "suggested_amount": max(MIN_BET_AMOUNT, (amount // MIN_BET_AMOUNT) * MIN_BET_AMOUNT),
                })

    return suggestions[:MAX_BET_SUGGESTIONS]


def _allocate_budget(budget: int, partners: dict) -> dict:
    """予算を配分する."""
    high_count = len(partners.get("high_confidence", []))
    medium_count = len(partners.get("medium_confidence", []))
    value_count = len(partners.get("value_picks", []))

    # 実際の相手馬数に基づいて配分を調整
    total_count = high_count + medium_count + value_count
    if total_count == 0:
        return {
            "total_budget": budget,
            "high_confidence_allocation": 0,
            "medium_confidence_allocation": 0,
            "value_allocation": 0,
        }

    # 相手馬が存在するカテゴリにのみ配分
    high_allocation = int(budget * HIGH_CONFIDENCE_RATIO) if high_count > 0 else 0
    medium_allocation = int(budget * MEDIUM_CONFIDENCE_RATIO) if medium_count > 0 else 0
    value_allocation = int(budget * VALUE_RATIO) if value_count > 0 else 0

    # 残額を再配分
    total_allocated = high_allocation + medium_allocation + value_allocation
    if total_allocated < budget:
        remainder = budget - total_allocated
        if high_count > 0:
            high_allocation += remainder
        elif medium_count > 0:
            medium_allocation += remainder
        elif value_count > 0:
            value_allocation += remainder

    return {
        "total_budget": budget,
        "high_confidence_allocation": high_allocation,
        "medium_confidence_allocation": medium_allocation,
        "value_allocation": value_allocation,
    }


def _generate_overall_comment(
    axis_info: list[dict],
    partners: dict,
    excluded: list[dict],
) -> str:
    """総合コメントを生成する."""
    axis_nums = [str(a["number"]) for a in axis_info]
    axis_str = "・".join(axis_nums)

    high = partners.get("high_confidence", [])
    medium = partners.get("medium_confidence", [])
    value = partners.get("value_picks", [])

    parts = [f"{axis_str}番軸"]

    if high:
        high_nums = [str(h["number"]) for h in high]
        parts.append(f"なら{high_nums[0]}番相手が本線")

    if medium:
        medium_nums = [str(m["number"]) for m in medium[:2]]
        parts.append(f"{','.join(medium_nums)}番も押さえたい")

    if value:
        value_nums = [str(v["number"]) for v in value[:1]]
        parts.append(f"{value_nums[0]}番は穴として注目")

    if excluded:
        excluded_nums = [str(e["number"]) for e in excluded[:2]]
        parts.append(f"{','.join(excluded_nums)}番は消し")

    return "。".join(parts) + "。"
