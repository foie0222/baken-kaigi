"""買い目提案ツール.

既存の分析ツールの内部関数を再利用し、
レース分析から買い目生成・予算配分までを一括で行う統合ツール。
"""

import math

import requests
from strands import tool

from .bet_analysis import (
    BET_TYPE_NAMES,
    _calculate_expected_value,
)
from .pace_analysis import (
    _assess_race_difficulty,
    _predict_pace,
)
from .risk_analysis import (
    _assess_skip_recommendation,
)

# =============================================================================
# ツール結果キャッシュ（セパレータ復元用）
# =============================================================================

# NOTE: AgentCore Runtime は各セッションを独立した microVM で実行するため、
# 並行リクエストによる競合状態は発生しない。
_last_proposal_result: dict | None = None


def get_last_proposal_result() -> dict | None:
    """キャッシュされた最新のツール結果を取得し、キャッシュをクリアする."""
    global _last_proposal_result
    result = _last_proposal_result
    _last_proposal_result = None
    return result


# =============================================================================
# 定数
# =============================================================================

# 軸馬選定: 複合スコアの重み
WEIGHT_AI_SCORE = 0.5
WEIGHT_ODDS_GAP = 0.3
WEIGHT_PACE_COMPAT = 0.2

# 券種選定: 難易度と券種のマッピング
DIFFICULTY_BET_TYPES = {
    1: ["quinella", "exacta"],
    2: ["quinella", "exacta"],
    3: ["quinella", "trio"],
    4: ["trio", "quinella_place"],
    5: ["quinella_place"],
}

# 予算配分: 信頼度別の配分比率
ALLOCATION_HIGH = 0.50
ALLOCATION_MEDIUM = 0.30
ALLOCATION_LOW = 0.20

# トリガミ除外閾値
TORIGAMI_COMPOSITE_ODDS_THRESHOLD = 2.0

# 見送りゲート閾値
SKIP_GATE_THRESHOLD = 7

# 見送り時の予算削減比率
SKIP_BUDGET_REDUCTION = 0.5

# 相手馬の最大数
MAX_PARTNERS = 4

# 買い目の最大数
MAX_BETS = 8

# 最低掛け金
MIN_BET_AMOUNT = 100

# 軸馬の最大数
MAX_AXIS_HORSES = 2

# オッズ乖離スコア: AI上位なのに人気が低い馬にボーナス
ODDS_GAP_BONUS_THRESHOLD = 5  # AI上位5位以内で人気が5番人気以下

# 券種別オッズ推定の補正係数（単勝オッズの積からの補正）
# 参考: JRA統計の券種別平均還元率と組み合わせ数から算出
BET_TYPE_ODDS_MULTIPLIER = {
    "quinella": 0.85,        # 馬連: √(o1*o2) * 0.85
    "quinella_place": 0.45,  # ワイド: √(o1*o2) * 0.45（3着内なので低い）
    "exacta": 1.7,           # 馬単: √(o1*o2) * 1.7（着順指定で高い）
    "trio": 1.5,             # 三連複: ∛(o1*o2*o3) * 1.5
    "trifecta": 4.0,         # 三連単: ∛(o1*o2*o3) * 4.0（着順指定で非常に高い）
}

# 脚質相性: ペースと脚質の相性マッピング
PACE_STYLE_COMPAT = {
    "ハイ": {"差し": 1.0, "追込": 1.0, "自在": 0.5, "先行": -0.5, "逃げ": -1.0},
    "ミドル": {"先行": 0.5, "差し": 0.5, "自在": 0.5, "逃げ": 0.0, "追込": 0.0},
    "スロー": {"逃げ": 1.0, "先行": 1.0, "自在": 0.5, "差し": -0.5, "追込": -1.0},
}


# =============================================================================
# Phase 2: 軸馬選定
# =============================================================================


def _calculate_composite_score(
    horse_number: int,
    runners_data: list[dict],
    ai_predictions: list[dict],
    predicted_pace: str = "",
    running_styles: list[dict] | None = None,
) -> float:
    """AI指数順位 x オッズ乖離 x 展開相性の複合スコアを計算する.

    Args:
        horse_number: 馬番
        runners_data: 出走馬データ
        ai_predictions: AI予想データ
        predicted_pace: 予想ペース
        running_styles: 脚質データ

    Returns:
        複合スコア（0-100）
    """
    running_styles = running_styles or []

    # AI順位スコア（1位=100, 2位=90, ...）
    ai_score = 0.0
    ai_rank = 99
    for pred in ai_predictions:
        if int(pred.get("horse_number", 0)) == horse_number:
            ai_rank = int(pred.get("rank", 99))
            # 順位ベースのスコア（1位=100, 18位=15）
            ai_score = max(0.0, 100.0 - (ai_rank - 1) * 5.0)
            break

    # オッズ乖離スコア
    odds_gap_score = 50.0  # デフォルト
    runner = next((r for r in runners_data if r.get("horse_number") == horse_number), None)
    if runner:
        popularity = runner.get("popularity") or 99
        # AI上位なのにオッズが高い = 市場の見落とし = ボーナス
        if ai_rank <= ODDS_GAP_BONUS_THRESHOLD and popularity > ODDS_GAP_BONUS_THRESHOLD:
            odds_gap_score = 80.0 + (popularity - ai_rank) * 2
        elif ai_rank <= 3 and popularity <= 3:
            odds_gap_score = 60.0  # 順当
        elif ai_rank > ODDS_GAP_BONUS_THRESHOLD and popularity <= 3:
            odds_gap_score = 20.0  # 過剰人気
        else:
            odds_gap_score = 50.0

    # 展開相性スコア
    pace_score = 50.0  # デフォルト
    if predicted_pace and running_styles:
        style_map = {r.get("horse_number"): r.get("running_style", "不明") for r in running_styles}
        style = style_map.get(horse_number, "不明")
        compat = PACE_STYLE_COMPAT.get(predicted_pace, {})
        pace_value = compat.get(style, 0.0)
        pace_score = 50.0 + pace_value * 25.0  # -1.0~1.0 -> 25~75

    # 加重平均
    composite = (
        ai_score * WEIGHT_AI_SCORE
        + odds_gap_score * WEIGHT_ODDS_GAP
        + pace_score * WEIGHT_PACE_COMPAT
    )
    return round(min(100, max(0, composite)), 1)


def _select_axis_horses(
    runners_data: list[dict],
    ai_predictions: list[dict],
    predicted_pace: str = "",
    running_styles: list[dict] | None = None,
    user_axis: list[int] | None = None,
) -> list[dict]:
    """軸馬を自動選定する.

    user_axisが指定されている場合はそれを使用し、
    未指定の場合はAI指数上位から複合スコアで選定する。

    Args:
        runners_data: 出走馬データ
        ai_predictions: AI予想データ
        predicted_pace: 予想ペース
        running_styles: 脚質データ
        user_axis: ユーザー指定の軸馬番号リスト

    Returns:
        軸馬リスト（horse_number, horse_name, composite_score）
    """
    runners_map = {r.get("horse_number"): r for r in runners_data}

    if user_axis:
        # ユーザー指定の軸馬（出走馬に存在する馬番のみ採用）
        valid_axis = [hn for hn in user_axis if hn in runners_map][:MAX_AXIS_HORSES]
        if valid_axis:
            result = []
            for hn in valid_axis:
                runner = runners_map.get(hn, {})
                score = _calculate_composite_score(
                    hn, runners_data, ai_predictions, predicted_pace, running_styles
                )
                result.append({
                    "horse_number": hn,
                    "horse_name": runner.get("horse_name", ""),
                    "composite_score": score,
                })
            return result
        # 有効な馬番がなければ自動選定にフォールバック

    # 自動選定: 全馬の複合スコアを計算
    scored = []
    for runner in runners_data:
        hn = runner.get("horse_number")
        score = _calculate_composite_score(
            hn, runners_data, ai_predictions, predicted_pace, running_styles
        )
        scored.append({
            "horse_number": hn,
            "horse_name": runner.get("horse_name", ""),
            "composite_score": score,
        })

    # スコア降順でソート
    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    return scored[:MAX_AXIS_HORSES]


# =============================================================================
# Phase 3: 券種自動選定
# =============================================================================


def _select_bet_types_by_difficulty(
    difficulty_stars: int,
    preferred_bet_types: list[str] | None = None,
) -> list[str]:
    """レース難易度から推奨券種を選定する.

    Args:
        difficulty_stars: レース難易度（1-5）
        preferred_bet_types: ユーザー指定の券種リスト

    Returns:
        推奨券種リスト
    """
    if preferred_bet_types:
        return preferred_bet_types

    stars = max(1, min(5, difficulty_stars))
    return DIFFICULTY_BET_TYPES[stars]


# =============================================================================
# Phase 4: 買い目生成 + トリガミチェック
# =============================================================================


def _estimate_bet_odds(odds_list: list, bet_type: str) -> float:
    """単勝オッズから券種別の推定オッズを計算する.

    馬連・馬単・三連複・三連単などの実際のオッズは
    単勝オッズの積と券種特性から推定する。

    Args:
        odds_list: 各馬の単勝オッズリスト（float, int, Decimal を許容）
        bet_type: 券種コード

    Returns:
        推定オッズ（0以下なら算出不可）
    """
    valid = [float(o) for o in odds_list if o > 0]
    if not valid:
        return 0.0

    multiplier = BET_TYPE_ODDS_MULTIPLIER.get(bet_type, 1.0)

    if len(valid) == 2:
        # 2頭の組み合わせ: 幾何平均 × 補正係数
        geo_mean = math.sqrt(valid[0] * valid[1])
        return round(geo_mean * multiplier, 1)
    elif len(valid) >= 3:
        # 3頭の組み合わせ: 幾何平均 × 補正係数
        product = 1.0
        for o in valid[:3]:
            product *= o
        geo_mean = product ** (1 / 3)
        return round(geo_mean * multiplier, 1)
    else:
        # 1頭の場合はそのまま
        return round(valid[0] * multiplier, 1)


def _generate_bet_candidates(
    axis_horses: list[dict],
    runners_data: list[dict],
    ai_predictions: list[dict],
    bet_types: list[str],
    total_runners: int,
    race_conditions: list[str] | None = None,
    predicted_pace: str = "",
    running_styles: list[dict] | None = None,
) -> list[dict]:
    """買い目候補を生成し、トリガミチェックを行う.

    Args:
        axis_horses: 軸馬リスト
        runners_data: 出走馬データ
        ai_predictions: AI予想データ
        bet_types: 券種リスト
        total_runners: 出走頭数
        race_conditions: レース条件
        predicted_pace: 予想ペース
        running_styles: 脚質データ

    Returns:
        買い目候補リスト（トリガミ除外済み、期待値順ソート）
    """
    race_conditions = race_conditions or []
    running_styles = running_styles or []

    axis_numbers = {a["horse_number"] for a in axis_horses}
    runners_map = {r.get("horse_number"): r for r in runners_data}

    # 相手馬候補: 軸馬以外の複合スコア上位
    partner_scores = []
    for runner in runners_data:
        hn = runner.get("horse_number")
        if hn in axis_numbers:
            continue
        score = _calculate_composite_score(
            hn, runners_data, ai_predictions, predicted_pace, running_styles
        )
        partner_scores.append({
            "horse_number": hn,
            "composite_score": score,
        })
    partner_scores.sort(key=lambda x: x["composite_score"], reverse=True)
    partners = partner_scores[:MAX_PARTNERS]

    bets = []
    for bet_type in bet_types:
        # 単勝/複勝は軸馬のみで買い目生成（相手馬不要）
        if bet_type in ("win", "place"):
            for axis in axis_horses:
                axis_hn = axis["horse_number"]
                axis_runner = runners_map.get(axis_hn, {})
                axis_pop = axis_runner.get("popularity") or 99
                axis_odds = axis_runner.get("odds") or 0

                ev = _calculate_expected_value(
                    axis_odds, axis_pop, bet_type, total_runners, race_conditions
                )

                if axis["composite_score"] >= 70:
                    confidence = "high"
                elif axis["composite_score"] >= 50:
                    confidence = "medium"
                else:
                    confidence = "low"

                bet_type_name = BET_TYPE_NAMES.get(bet_type, bet_type)
                axis_name = axis_runner.get("horse_name", "")

                # AI順位を取得（DynamoDB Decimal対策でint正規化）
                ai_rank_map = {
                    int(p.get("horse_number", 0)): int(p.get("rank", 99))
                    for p in ai_predictions
                }
                axis_ai = ai_rank_map.get(axis_hn, 99)
                parts = []
                if axis_ai <= 3:
                    parts.append(f"AI{axis_ai}位")
                ev_val = ev.get("expected_return", 0)
                rating = ev.get("value_rating", "")
                if rating:
                    parts.append(f"期待値{ev_val}（{rating}）")
                parts.append(f"{bet_type_name} {axis_hn}番{axis_name}")
                reasoning = "。".join(parts)

                bets.append({
                    "bet_type": bet_type,
                    "bet_type_name": bet_type_name,
                    "horse_numbers": [axis_hn],
                    "bet_display": str(axis_hn),
                    "confidence": confidence,
                    "expected_value": ev.get("expected_return", 0),
                    "composite_odds": axis_odds,
                    "reasoning": reasoning,
                    "bet_count": 1,
                })
            continue


        for axis in axis_horses:
            axis_hn = axis["horse_number"]
            axis_runner = runners_map.get(axis_hn, {})
            axis_pop = axis_runner.get("popularity") or 99
            axis_odds = axis_runner.get("odds") or 0

            for partner in partners:
                partner_hn = partner["horse_number"]
                partner_runner = runners_map.get(partner_hn, {})
                partner_pop = partner_runner.get("popularity") or 99
                partner_odds = partner_runner.get("odds") or 0

                # 馬番表示
                if bet_type in ("quinella", "quinella_place"):
                    horse_numbers = sorted([axis_hn, partner_hn])
                    bet_display = f"{horse_numbers[0]}-{horse_numbers[1]}"
                elif bet_type == "exacta":
                    horse_numbers = [axis_hn, partner_hn]
                    bet_display = f"{axis_hn}-{partner_hn}"
                elif bet_type in ("trio", "trifecta"):
                    # 3連系は3頭必要なので、partner_scoresからもう1頭追加
                    continue  # 後で処理
                else:
                    horse_numbers = [axis_hn, partner_hn]
                    bet_display = f"{axis_hn}-{partner_hn}"

                # 推定オッズ計算（単勝オッズから券種別に推定）
                estimated_odds = _estimate_bet_odds(
                    [axis_odds, partner_odds], bet_type
                )

                # 期待値計算（推定オッズと代表人気で計算）
                # 人気は2頭の平均を使用
                avg_pop = max(1, (axis_pop + partner_pop) // 2)
                ev = _calculate_expected_value(
                    estimated_odds, avg_pop, bet_type, total_runners, race_conditions
                )

                # トリガミチェック（推定オッズが閾値未満なら除外）
                if 0 < estimated_odds < TORIGAMI_COMPOSITE_ODDS_THRESHOLD:
                    continue  # トリガミ除外

                # 信頼度判定
                avg_score = (axis["composite_score"] + partner["composite_score"]) / 2
                if avg_score >= 70:
                    confidence = "high"
                elif avg_score >= 50:
                    confidence = "medium"
                else:
                    confidence = "low"

                # reasoning生成
                axis_name = axis_runner.get("horse_name", "")
                partner_name = partner_runner.get("horse_name", "")
                reasoning = _generate_bet_reasoning(
                    axis_hn, axis_name, axis_pop,
                    partner_hn, partner_name, partner_pop,
                    bet_type, bet_display, ev, ai_predictions,
                )

                bets.append({
                    "bet_type": bet_type,
                    "bet_type_name": BET_TYPE_NAMES.get(bet_type, bet_type),
                    "horse_numbers": horse_numbers,
                    "bet_display": bet_display,
                    "confidence": confidence,
                    "expected_value": ev.get("expected_return", 0),
                    "composite_odds": estimated_odds,
                    "reasoning": reasoning,
                    "bet_count": 1,
                })

        # 3連系の処理
        if bet_type in ("trio", "trifecta") and len(partners) >= 2:
            from itertools import combinations as combs

            for axis in axis_horses:
                axis_hn = axis["horse_number"]
                axis_runner = runners_map.get(axis_hn, {})
                axis_pop = axis_runner.get("popularity") or 99
                axis_odds = axis_runner.get("odds") or 0

                for p1, p2 in combs(partners[:MAX_PARTNERS], 2):
                    p1_hn = p1["horse_number"]
                    p2_hn = p2["horse_number"]
                    p1_runner = runners_map.get(p1_hn, {})
                    p2_runner = runners_map.get(p2_hn, {})
                    p1_odds = p1_runner.get("odds") or 0
                    p2_odds = p2_runner.get("odds") or 0

                    if bet_type == "trio":
                        horse_numbers = sorted([axis_hn, p1_hn, p2_hn])
                        bet_display = f"{horse_numbers[0]}-{horse_numbers[1]}-{horse_numbers[2]}"
                    else:
                        horse_numbers = [axis_hn, p1_hn, p2_hn]
                        bet_display = f"{axis_hn}-{p1_hn}-{p2_hn}"

                    p1_pop = p1_runner.get("popularity") or 99
                    p2_pop = p2_runner.get("popularity") or 99

                    # 推定オッズ（券種別補正係数を適用）
                    estimated_odds = _estimate_bet_odds(
                        [axis_odds, p1_odds, p2_odds], bet_type
                    )

                    # 期待値（3頭の平均人気で計算）
                    avg_pop = max(1, (axis_pop + p1_pop + p2_pop) // 3)
                    ev = _calculate_expected_value(
                        estimated_odds, avg_pop, bet_type, total_runners, race_conditions
                    )

                    # トリガミチェック
                    if 0 < estimated_odds < TORIGAMI_COMPOSITE_ODDS_THRESHOLD:
                        continue

                    avg_score = (axis["composite_score"] + p1["composite_score"] + p2["composite_score"]) / 3
                    if avg_score >= 70:
                        confidence = "high"
                    elif avg_score >= 50:
                        confidence = "medium"
                    else:
                        confidence = "low"

                    reasoning = f"{axis_hn}番軸-{p1_hn}番-{p2_hn}番の{BET_TYPE_NAMES.get(bet_type, bet_type)}"

                    bets.append({
                        "bet_type": bet_type,
                        "bet_type_name": BET_TYPE_NAMES.get(bet_type, bet_type),
                        "horse_numbers": horse_numbers,
                        "bet_display": bet_display,
                        "confidence": confidence,
                        "expected_value": ev.get("expected_return", 0),
                        "composite_odds": estimated_odds,
                        "reasoning": reasoning,
                        "bet_count": 1,
                    })

    # 期待値降順ソート
    bets.sort(key=lambda x: x["expected_value"], reverse=True)
    return bets[:MAX_BETS]


def _generate_bet_reasoning(
    axis_hn: int,
    axis_name: str,
    axis_pop: int,
    partner_hn: int,
    partner_name: str,
    partner_pop: int,
    bet_type: str,
    bet_display: str,
    ev: dict,
    ai_predictions: list[dict],
) -> str:
    """買い目の根拠テキストを生成する."""
    # AI順位を取得（DynamoDB Decimal対策でint正規化）
    ai_rank_map = {int(p.get("horse_number", 0)): int(p.get("rank", 99)) for p in ai_predictions}
    axis_ai = ai_rank_map.get(axis_hn, 99)
    partner_ai = ai_rank_map.get(partner_hn, 99)

    parts = []
    if axis_ai <= 3 and partner_ai <= 3:
        parts.append(f"AI上位{axis_ai}位-{partner_ai}位の組み合わせ")
    elif axis_ai <= 3:
        parts.append(f"AI{axis_ai}位{axis_hn}番{axis_name}軸")

    ev_val = ev.get("expected_return", 0)
    rating = ev.get("value_rating", "")
    if rating:
        parts.append(f"期待値{ev_val}（{rating}）")

    bet_name = BET_TYPE_NAMES.get(bet_type, bet_type)
    parts.append(f"{bet_name} {bet_display}")

    return "。".join(parts)


# =============================================================================
# Phase 5: 予算配分
# =============================================================================


def _allocate_budget(
    bets: list[dict],
    budget: int,
) -> list[dict]:
    """信頼度別に予算を配分する.

    高信頼: 50% / 中信頼: 30% / 穴狙い: 20%
    100円単位に丸め、最低100円保証。

    Args:
        bets: 買い目候補リスト
        budget: 総予算

    Returns:
        金額付き買い目リスト
    """
    if not bets or budget <= 0:
        return bets

    # 信頼度別に分類
    high = [b for b in bets if b.get("confidence") == "high"]
    medium = [b for b in bets if b.get("confidence") == "medium"]
    value = [b for b in bets if b.get("confidence") == "low"]

    # 各グループの予算枠を計算
    # 存在するグループのみに配分
    groups = []
    if high:
        groups.append(("high", high, ALLOCATION_HIGH))
    if medium:
        groups.append(("medium", medium, ALLOCATION_MEDIUM))
    if value:
        groups.append(("low", value, ALLOCATION_LOW))

    if not groups:
        return bets

    # 予算で買える最大買い目数（最低100円/点）
    max_affordable = budget // MIN_BET_AMOUNT
    if max_affordable <= 0:
        return bets

    # 買い目数が予算を超過する場合、高信頼度順に絞り込み
    if len(bets) > max_affordable:
        priority = {"high": 0, "medium": 1, "low": 2}
        bets.sort(key=lambda b: (priority.get(b.get("confidence", "low"), 2), -b.get("expected_value", 0)))
        bets = bets[:max_affordable]
        # 再分類
        high = [b for b in bets if b.get("confidence") == "high"]
        medium = [b for b in bets if b.get("confidence") == "medium"]
        value = [b for b in bets if b.get("confidence") == "low"]
        groups = []
        if high:
            groups.append(("high", high, ALLOCATION_HIGH))
        if medium:
            groups.append(("medium", medium, ALLOCATION_MEDIUM))
        if value:
            groups.append(("low", value, ALLOCATION_LOW))
        if not groups:
            return bets

    # 比率を正規化
    total_ratio = sum(g[2] for g in groups)
    normalized = [(g[0], g[1], g[2] / total_ratio) for g in groups]

    total_amount = 0
    for _, group_bets, ratio in normalized:
        group_budget = int(budget * ratio)
        # 期待値ベースの傾斜配分
        evs = [max(0, b.get("expected_value", 0)) for b in group_bets]
        total_ev = sum(evs)
        if total_ev > 0:
            # 期待値に比例して配分（100円単位に丸め、最低100円保証）
            for i, bet in enumerate(group_bets):
                raw = group_budget * evs[i] / total_ev
                bet["amount"] = max(MIN_BET_AMOUNT, int(math.floor(raw / 100) * 100))
                total_amount += bet["amount"]
        else:
            # 期待値が全て0の場合は均等配分
            per_bet = max(MIN_BET_AMOUNT, int(math.floor(group_budget / len(group_bets) / 100) * 100))
            for bet in group_bets:
                bet["amount"] = per_bet
                total_amount += per_bet

    # 予算超過時は低信頼度から金額削減
    if total_amount > budget:
        overage = total_amount - budget
        # 低→中→高の順で削減
        for b in reversed(bets):
            if overage <= 0:
                break
            reducible = b["amount"] - MIN_BET_AMOUNT
            if reducible > 0:
                reduction = min(reducible, overage)
                reduction = (reduction // 100) * 100
                if reduction > 0:
                    b["amount"] -= reduction
                    overage -= reduction

    # 余剰予算を期待値の高い買い目に追加配分
    remaining = budget - sum(b.get("amount", 0) for b in bets if "amount" in b)
    if remaining >= 100:
        # 期待値降順でソートした順に100円ずつ追加
        sorted_by_ev = sorted(
            [b for b in bets if "amount" in b],
            key=lambda b: b.get("expected_value", 0),
            reverse=True,
        )
        for bet in sorted_by_ev:
            if remaining < 100:
                break
            add = (remaining // 100) * 100
            # 1回で全額追加せず、100円ずつ配分してバランスを保つ
            add = min(add, 100)
            bet["amount"] += add
            remaining -= add
        # まだ残っていれば繰り返し
        while remaining >= 100:
            for bet in sorted_by_ev:
                if remaining < 100:
                    break
                bet["amount"] += 100
                remaining -= 100

    return bets


# =============================================================================
# Phase 6: AI合議レベル判定
# =============================================================================


def _assess_ai_consensus(ai_predictions: list[dict]) -> str:
    """AI予想の合議レベルを判定する.

    単一ソースなので、上位2頭のスコア差で判定する。

    Args:
        ai_predictions: AI予想データ

    Returns:
        合議レベル文字列
    """
    if not ai_predictions or len(ai_predictions) < 2:
        return "データ不足"

    sorted_preds = sorted(ai_predictions, key=lambda x: x.get("score", 0), reverse=True)
    top_score = sorted_preds[0].get("score", 0)
    second_score = sorted_preds[1].get("score", 0)
    gap = top_score - second_score

    if gap >= 50:
        return "明確な上位"
    elif gap >= 20:
        return "概ね合意"
    elif gap >= 10:
        return "やや接戦"
    else:
        return "混戦"


# =============================================================================
# 統合関数（テスト用に公開）
# =============================================================================


def _generate_bet_proposal_impl(
    race_id: str,
    budget: int,
    runners_data: list[dict],
    ai_predictions: list[dict],
    race_name: str = "",
    race_conditions: list[str] | None = None,
    venue: str = "",
    total_runners: int = 18,
    running_styles: list[dict] | None = None,
    preferred_bet_types: list[str] | None = None,
    axis_horses: list[int] | None = None,
) -> dict:
    """買い目提案の統合実装（テスト用に公開）.

    Args:
        race_id: レースID
        budget: 予算
        runners_data: 出走馬データ
        ai_predictions: AI予想データ
        race_name: レース名
        race_conditions: レース条件
        venue: 競馬場名
        total_runners: 出走頭数
        running_styles: 脚質データ
        preferred_bet_types: ユーザー指定の券種リスト
        axis_horses: ユーザー指定の軸馬番号リスト

    Returns:
        統合提案結果
    """
    race_conditions = race_conditions or []
    running_styles = running_styles or []

    # Phase 2: ペース予想
    front_runners = 0
    for rs in running_styles:
        if rs.get("running_style") == "逃げ":
            front_runners += 1
    predicted_pace = _predict_pace(front_runners, total_runners) if running_styles else ""

    # Phase 2: 軸馬選定
    selected_axis = _select_axis_horses(
        runners_data, ai_predictions, predicted_pace, running_styles, axis_horses
    )

    # Phase 3: レース難易度判定 + 券種選定
    difficulty = _assess_race_difficulty(
        total_runners, race_conditions, venue, runners_data
    )
    bet_types = _select_bet_types_by_difficulty(
        difficulty["difficulty_stars"], preferred_bet_types
    )

    # Phase 6: 見送りゲート
    skip = _assess_skip_recommendation(
        total_runners=total_runners,
        race_conditions=race_conditions,
        venue=venue,
        runners_data=runners_data,
        ai_predictions=ai_predictions,
        predicted_pace=predicted_pace,
    )

    effective_budget = budget
    if skip["skip_score"] >= SKIP_GATE_THRESHOLD:
        effective_budget = int(budget * SKIP_BUDGET_REDUCTION)

    # Phase 4: 買い目生成
    bets = _generate_bet_candidates(
        axis_horses=selected_axis,
        runners_data=runners_data,
        ai_predictions=ai_predictions,
        bet_types=bet_types,
        total_runners=total_runners,
        race_conditions=race_conditions,
        predicted_pace=predicted_pace,
        running_styles=running_styles,
    )

    # Phase 5: 予算配分
    bets = _allocate_budget(bets, effective_budget)

    # 合計金額
    total_amount = sum(b.get("amount", 0) for b in bets)

    # AI合議レベル
    ai_consensus = _assess_ai_consensus(ai_predictions)

    # 分析コメント生成
    analysis_comment = _generate_analysis_comment(
        selected_axis, difficulty, predicted_pace, skip, ai_consensus, bets
    )

    return {
        "race_id": race_id,
        "race_summary": {
            "race_name": race_name,
            "difficulty_stars": difficulty["difficulty_stars"],
            "predicted_pace": predicted_pace or "不明",
            "ai_consensus_level": ai_consensus,
            "skip_score": skip["skip_score"],
            "skip_recommendation": skip["recommendation"],
        },
        "proposed_bets": bets,
        "total_amount": total_amount,
        "budget_remaining": effective_budget - total_amount,
        "analysis_comment": analysis_comment,
        "disclaimer": "データ分析に基づく情報提供です。最終判断はご自身でお願いします。",
    }


def _generate_analysis_comment(
    axis_horses: list[dict],
    difficulty: dict,
    predicted_pace: str,
    skip: dict,
    ai_consensus: str,
    bets: list[dict],
) -> str:
    """分析ナラティブを生成する."""
    parts = []

    # 軸馬
    axis_names = [f"{a['horse_number']}番" for a in axis_horses]
    parts.append(f"軸馬: {'・'.join(axis_names)}")

    # 難易度
    stars = "★" * difficulty["difficulty_stars"] + "☆" * (5 - difficulty["difficulty_stars"])
    parts.append(f"レース難易度: {stars}（{difficulty['difficulty_label']}）")

    # ペース
    if predicted_pace:
        parts.append(f"予想ペース: {predicted_pace}")

    # AI合議
    parts.append(f"AI合議: {ai_consensus}")

    # 見送り
    if skip["skip_score"] >= SKIP_GATE_THRESHOLD:
        parts.append(f"見送りスコア{skip['skip_score']}/10。予算を50%削減して提案")
    elif skip["skip_score"] >= 5:
        parts.append(f"見送りスコア{skip['skip_score']}/10。慎重な検討を推奨")

    # 買い目数
    parts.append(f"提案{len(bets)}点")

    return "。".join(parts)


# =============================================================================
# @tool 関数
# =============================================================================


@tool
def generate_bet_proposal(
    race_id: str,
    budget: int,
    preferred_bet_types: list[str] | None = None,
    axis_horses: list[int] | None = None,
) -> dict:
    """レース分析に基づき、買い目の提案を一括生成する.

    AI指数・レース難易度・展開予想を統合し、
    軸馬選定 → 券種選定 → 買い目生成 → 予算配分を自動で行う。
    見送りスコアが高い場合は予算を50%削減して提案する。

    Args:
        race_id: レースID (例: "20260201_05_11")
        budget: 予算（円）
        preferred_bet_types: 券種の指定リスト (省略時はレース難易度から自動選定)
            "win", "place", "quinella", "quinella_place", "exacta", "trio", "trifecta"
        axis_horses: 軸馬の馬番リスト (省略時はAI指数上位から自動選定)

    Returns:
        提案結果:
        - race_summary: レース概要（難易度、ペース、AI合議、見送りスコア）
        - proposed_bets: 提案買い目リスト（券種、馬番、金額、期待値、合成オッズ）
        - total_amount: 合計金額
        - budget_remaining: 残り予算
        - analysis_comment: 分析ナラティブ
        - disclaimer: 免責事項
    """
    global _last_proposal_result
    _last_proposal_result = None  # 呼び出し単位でキャッシュをリセット
    try:
        # データ収集
        from .race_data import _fetch_race_detail, _extract_race_conditions
        from .ai_prediction import get_ai_prediction
        from .pace_analysis import _get_running_styles

        # レースデータ取得
        race_detail = _fetch_race_detail(race_id)
        race = race_detail.get("race", {})
        runners_data = race_detail.get("runners", [])
        race_conditions = _extract_race_conditions(race)
        venue = race.get("venue", "")
        total_runners = race.get("horse_count", len(runners_data))
        race_name = race.get("race_name", "")

        # AI予想取得
        ai_result = get_ai_prediction(race_id)
        ai_predictions = []
        if isinstance(ai_result, dict):
            sources = ai_result.get("sources", [])
            if sources:
                ai_predictions = sources[0].get("predictions", [])
            elif ai_result.get("predictions"):
                ai_predictions = ai_result["predictions"]

        # 脚質データ取得
        running_styles = _get_running_styles(race_id)

        result = _generate_bet_proposal_impl(
            race_id=race_id,
            budget=budget,
            runners_data=runners_data,
            ai_predictions=ai_predictions,
            race_name=race_name,
            race_conditions=race_conditions,
            venue=venue,
            total_runners=total_runners,
            running_styles=running_styles,
            preferred_bet_types=preferred_bet_types,
            axis_horses=axis_horses,
        )
        if "error" not in result:
            _last_proposal_result = result
        return result
    except requests.RequestException as e:
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        return {"error": f"提案生成に失敗しました: {str(e)}"}
