"""相手馬選定ツール.

軸馬に対する相手馬を選定し、買い目の組み立てを支援する。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# スコア閾値
SCORE_HIGH_CONFIDENCE = 75
SCORE_MEDIUM_CONFIDENCE = 60
SCORE_VALUE_PICK = 45

# 予算配分比率
HIGH_CONFIDENCE_RATIO = 0.5
MEDIUM_CONFIDENCE_RATIO = 0.3
VALUE_RATIO = 0.2


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
        # 出走馬リスト取得
        runners = _get_runners(race_id)
        if not runners:
            return {"error": "出走馬データが取得できませんでした", "race_id": race_id}

        # オッズデータ取得
        odds_data = _get_current_odds(race_id)

        # 脚質データ取得
        running_styles = _get_running_styles(race_id)

        # 各馬のスコアを計算
        horse_scores = _calculate_horse_scores(race_id, runners, running_styles)

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
            axis_info, partners, excluded, bet_type
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
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/runners",
            headers=get_headers(),
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
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/odds/win",
            headers=get_headers(),
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
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/running-styles",
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("running_styles", [])
    except requests.RequestException as e:
        logger.error(f"Failed to get running styles for race {race_id}: {e}")
        return []


def _calculate_horse_scores(
    race_id: str,
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
        score = 50
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
            score += 5
            reasons.append("脚質良好")
        elif style == "追込":
            risk_reasons.append("追込脚質")

        # 枠順評価
        if horse_number <= 4:
            score += 5
            reasons.append("内枠有利")
        elif horse_number >= 14:
            score -= 5
            risk_reasons.append("外枠不利")

        scores[horse_number] = {
            "score": min(100, max(0, score)),
            "reasons": reasons[:3],
            "risk_reasons": risk_reasons[:3],
        }

    return scores


def _evaluate_form(horse_id: str) -> tuple[int, list[str], list[str]]:
    """過去成績から評価する."""
    score_delta = 0
    reasons = []
    risk_reasons = []

    try:
        response = requests.get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": 5},
            headers=get_headers(),
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

                    if avg <= 3.0:
                        score_delta += 20
                        reasons.append("好成績継続")
                    elif avg <= 5.0:
                        score_delta += 10
                        reasons.append("安定した成績")
                    else:
                        score_delta -= 10
                        risk_reasons.append("成績不振")

                    if in_money >= 3:
                        score_delta += 5
                        reasons.append("連対率高い")
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
        score_info = horse_scores.get(horse_number, {"score": 50})

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
        elif score >= SCORE_VALUE_PICK and odds >= 10:
            partner["reasons"].append("オッズ妙味")
            value_picks.append(partner)

    # スコア順にソート
    high_confidence.sort(key=lambda x: x["score"], reverse=True)
    medium_confidence.sort(key=lambda x: x["score"], reverse=True)
    value_picks.sort(key=lambda x: x["score"], reverse=True)

    return {
        "high_confidence": high_confidence[:3],
        "medium_confidence": medium_confidence[:3],
        "value_picks": value_picks[:3],
    }


def _evaluate_odds_value(score: int, odds: float) -> str:
    """オッズの価値を評価する."""
    if odds <= 0:
        return "データなし"

    # スコアに対する期待オッズ
    if score >= SCORE_HIGH_CONFIDENCE:
        expected_odds = 5.0
    elif score >= SCORE_MEDIUM_CONFIDENCE:
        expected_odds = 10.0
    else:
        expected_odds = 20.0

    if odds < expected_odds * 0.7:
        return "過剰人気"
    elif odds > expected_odds * 1.5:
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
        if score < SCORE_VALUE_PICK or (odds > 0 and odds <= 5.0 and score < SCORE_MEDIUM_CONFIDENCE):
            runner = runner_map.get(horse_number, {})

            if not risk_reasons:
                risk_reasons = ["総合評価低"]

            risk_level = "消し推奨" if score < 40 else "注意"

            excluded.append({
                "number": horse_number,
                "name": runner.get("horse_name", ""),
                "reasons": risk_reasons,
                "risk_level": risk_level,
            })

    return excluded[:5]


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

    for i, partner in enumerate(all_partners[:6]):
        for axis in axis_horses:
            # 組み合わせ生成
            if bet_type in ["馬連", "ワイド"]:
                combination = f"{min(axis, partner['number'])}-{max(axis, partner['number'])}"
            else:
                combination = f"{axis}-{partner['number']}"

            # オッズ推定（単勝オッズから概算）
            axis_odds = odds_data.get(axis, 5.0)
            partner_odds = odds_data.get(partner["number"], 10.0)
            estimated_odds = (axis_odds * partner_odds) ** 0.5 * 1.2

            # 信頼度と金額
            if partner["score"] >= SCORE_HIGH_CONFIDENCE:
                confidence = "高"
                amount = int(budget * 0.15)
            elif partner["score"] >= SCORE_MEDIUM_CONFIDENCE:
                confidence = "中"
                amount = int(budget * 0.08)
            else:
                confidence = "低（穴狙い）"
                amount = int(budget * 0.04)

            suggestions.append({
                "bet_type": bet_type,
                "combination": combination,
                "estimated_odds": round(estimated_odds, 1),
                "confidence": confidence,
                "suggested_amount": max(100, (amount // 100) * 100),
            })

    return suggestions[:8]


def _allocate_budget(budget: int, partners: dict) -> dict:
    """予算を配分する."""
    high_count = len(partners.get("high_confidence", []))
    medium_count = len(partners.get("medium_confidence", []))
    value_count = len(partners.get("value_picks", []))

    total_count = high_count + medium_count + value_count
    if total_count == 0:
        return {
            "total_budget": budget,
            "high_confidence_allocation": 0,
            "medium_confidence_allocation": 0,
            "value_allocation": 0,
        }

    high_allocation = int(budget * HIGH_CONFIDENCE_RATIO)
    medium_allocation = int(budget * MEDIUM_CONFIDENCE_RATIO)
    value_allocation = int(budget * VALUE_RATIO)

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
    bet_type: str,
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
