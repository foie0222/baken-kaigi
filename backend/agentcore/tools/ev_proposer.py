"""EVベース買い目提案ツール.

LLMが調整した勝率と実オッズから期待値を計算し、
期待値が正の買い目を選定・予算配分する。
"""

import logging
from itertools import combinations, permutations

from strands import tool

from .bet_analysis import (
    BET_TYPE_NAMES,
    _harville_exacta,
    _harville_trifecta,
)
from .bet_proposal import (
    MIN_BET_AMOUNT,
    MAX_RACE_BUDGET_RATIO,
    DEFAULT_BASE_RATE,
    _allocate_budget,
    _allocate_budget_dutching,
    _invoke_haiku_narrator,
)
from .jravan_client import cached_get, get_api_url

logger = logging.getLogger(__name__)

# =============================================================================
# 好み設定 → preferred_bet_types マッピング
# =============================================================================
_current_betting_preference: dict | None = None


def set_betting_preference(preference: dict | None) -> None:
    """好み設定を注入する（agent.py から呼ばれる）."""
    global _current_betting_preference
    _current_betting_preference = preference


_BET_TYPE_PREFERENCE_MAP: dict[str, list[str]] = {
    "trio_focused": ["trio", "trifecta"],
    "exacta_focused": ["exacta", "quinella", "quinella_place"],
    "quinella_focused": ["quinella", "quinella_place"],
    "wide_focused": ["quinella_place", "quinella"],
}


def _resolve_bet_types(betting_preference: dict | None) -> list[str]:
    """好み設定から preferred_bet_types を解決する."""
    if not betting_preference:
        return DEFAULT_BET_TYPES
    pref = betting_preference.get("bet_type_preference")
    if not pref or pref == "auto":
        return DEFAULT_BET_TYPES
    return _BET_TYPE_PREFERENCE_MAP.get(pref, DEFAULT_BET_TYPES)


def _resolve_ev_filter(
    betting_preference: dict | None,
) -> tuple[float, float, float | None, float | None]:
    """好み設定から確率/EVフィルター値を解決する.

    Returns:
        (min_probability, min_ev, max_probability, max_ev)
        max は None = 上限なし
    """
    if not betting_preference:
        return (0.0, EV_THRESHOLD, None, None)
    max_prob_raw = betting_preference.get("max_probability")
    max_ev_raw = betting_preference.get("max_ev")
    return (
        float(betting_preference.get("min_probability", 0.0)),
        float(betting_preference.get("min_ev", EV_THRESHOLD)),
        float(max_prob_raw) if max_prob_raw is not None else None,
        float(max_ev_raw) if max_ev_raw is not None else None,
    )


# =============================================================================
# ツール結果キャッシュ（セパレータ復元用）
# =============================================================================
_last_ev_proposal_result: dict | None = None


def get_last_ev_proposal_result() -> dict | None:
    """キャッシュされた最新のEV提案結果を取得し、キャッシュをクリアする."""
    global _last_ev_proposal_result
    result = _last_ev_proposal_result
    _last_ev_proposal_result = None
    return result


# EV閾値: これ以上の期待値がある組合せのみ提案
EV_THRESHOLD = 1.0

# デフォルト券種リスト（preferred_bet_types未指定時）
DEFAULT_BET_TYPES = ["quinella", "exacta", "quinella_place", "trio"]

# 組合せ生成対象の最小確率（これ以下の馬は組合せに含めない）
MIN_PROB_FOR_COMBINATION = 0.02

def _fetch_all_odds(race_id: str) -> dict:
    """JRA-VAN APIから全券種オッズを取得."""
    response = cached_get(f"{get_api_url()}/races/{race_id}/odds")
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json()


# 昇順ソートする券種（着順を問わない）
_SORTED_BET_TYPES = {"quinella", "quinella_place", "trio"}


def _make_odds_key(horse_numbers: list[int], bet_type: str) -> str:
    """馬番リストからオッズ参照キーを生成.

    馬連/ワイド/三連複 → 昇順。馬単/三連単 → 着順のまま。
    単勝/複勝 → 馬番のみ。
    """
    if len(horse_numbers) == 1:
        return str(horse_numbers[0])
    nums = sorted(horse_numbers) if bet_type in _SORTED_BET_TYPES else horse_numbers
    return "-".join(str(n) for n in nums)


# 券種名 → レスポンスキー のマッピング
_BET_TYPE_TO_ODDS_KEY = {
    "win": "win",
    "place": "place",
    "quinella": "quinella",
    "quinella_place": "quinella_place",
    "exacta": "exacta",
    "trio": "trio",
    "trifecta": "trifecta",
}


def _lookup_real_odds(
    horse_numbers: list[int], bet_type: str, all_odds: dict,
) -> float:
    """実オッズを参照。見つからない場合は0.0."""
    odds_key = _BET_TYPE_TO_ODDS_KEY.get(bet_type)
    if not odds_key or odds_key not in all_odds:
        return 0.0

    odds_dict = all_odds[odds_key]
    key = _make_odds_key(horse_numbers, bet_type)

    if bet_type == "place":
        entry = odds_dict.get(key, {})
        return float(entry.get("min", 0)) if entry else 0.0

    return float(odds_dict.get(key, 0.0))


def _calculate_combination_probability(
    horse_numbers: list[int],
    bet_type: str,
    win_probs: dict[int, float],
    total_runners: int,
) -> float:
    """Harvilleモデルで組合せ確率を算出する."""
    if bet_type == "win":
        return win_probs.get(horse_numbers[0], 0.0)

    elif bet_type == "place":
        return min(1.0, win_probs.get(horse_numbers[0], 0.0) * 3)

    elif bet_type == "quinella":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        return _harville_exacta(p_a, p_b) + _harville_exacta(p_b, p_a)

    elif bet_type == "exacta":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        return _harville_exacta(p_a, p_b)

    elif bet_type == "quinella_place":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        prob = 0.0
        for hn_c, p_c in win_probs.items():
            if hn_c in set(horse_numbers):
                continue
            prob += _harville_trifecta(p_a, p_b, p_c)
            prob += _harville_trifecta(p_a, p_c, p_b)
            prob += _harville_trifecta(p_b, p_a, p_c)
            prob += _harville_trifecta(p_b, p_c, p_a)
            prob += _harville_trifecta(p_c, p_a, p_b)
            prob += _harville_trifecta(p_c, p_b, p_a)
        return prob

    elif bet_type == "trio":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        p_c = win_probs.get(horse_numbers[2], 0.0)
        return sum(
            _harville_trifecta(pa, pb, pc)
            for pa, pb, pc in permutations([p_a, p_b, p_c])
        )

    elif bet_type == "trifecta":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        p_c = win_probs.get(horse_numbers[2], 0.0)
        return _harville_trifecta(p_a, p_b, p_c)

    return 0.0


def _build_candidate(
    horse_numbers: list[int],
    bet_type: str,
    probability: float,
    estimated_odds: float,
    ev: float,
    runners_map: dict,
) -> dict:
    """買い目候補の辞書を構築する."""
    names = [runners_map.get(hn, {}).get("horse_name", f"{hn}番") for hn in horse_numbers]
    bet_type_name = BET_TYPE_NAMES.get(bet_type, bet_type)

    if len(names) == 1:
        display = f"{bet_type_name} {horse_numbers[0]}番 {names[0]}"
    elif len(names) == 2:
        display = f"{bet_type_name} {horse_numbers[0]}-{horse_numbers[1]}"
    else:
        display = f"{bet_type_name} {'-'.join(str(h) for h in horse_numbers)}"

    return {
        "bet_type": bet_type,
        "horse_numbers": horse_numbers,
        "amount": 0,
        "bet_count": 1,
        "bet_display": display,
        "expected_value": round(ev, 2),
        "composite_odds": round(estimated_odds, 1),
        "combination_probability": round(probability, 6),
        "reasoning": f"EV={ev:.2f} (確率{probability:.1%}×オッズ{estimated_odds:.1f}倍)",
    }


def _generate_ev_candidates(
    win_probs: dict[int, float],
    runners_map: dict[int, dict],
    bet_types: list[str],
    total_runners: int,
    all_odds: dict,
    ev_filter: tuple[float, float, float | None, float | None] | None = None,
) -> list[dict]:
    """全組合せのEVを計算し、フィルター条件を満たすものを返す."""
    min_prob_filter, min_ev_filter, max_prob_filter, max_ev_filter = ev_filter or (0.0, 0.0, None, None)

    eligible = sorted(
        [hn for hn, p in win_probs.items() if p >= min_prob_filter],
        key=lambda hn: win_probs[hn],
        reverse=True,
    )

    def _passes_filter(prob: float, ev: float) -> bool:
        if prob < min_prob_filter or ev < min_ev_filter:
            return False
        if max_prob_filter is not None and prob > max_prob_filter:
            return False
        if max_ev_filter is not None and ev > max_ev_filter:
            return False
        return True

    candidates = []

    for bet_type in bet_types:
        if bet_type in ("win", "place"):
            for hn in eligible:
                horse_numbers = [hn]
                prob = _calculate_combination_probability(
                    horse_numbers, bet_type, win_probs, total_runners,
                )
                real_odds = _lookup_real_odds(horse_numbers, bet_type, all_odds)
                ev = prob * real_odds if real_odds > 0 else 0.0
                if _passes_filter(prob, ev):
                    candidates.append(_build_candidate(
                        horse_numbers, bet_type, prob, real_odds, ev, runners_map,
                    ))

        elif bet_type in ("quinella", "exacta", "quinella_place"):
            for combo in combinations(eligible, 2):
                horse_numbers = list(combo)
                if bet_type == "exacta":
                    horse_numbers.sort(key=lambda h: win_probs.get(h, 0), reverse=True)
                prob = _calculate_combination_probability(
                    horse_numbers, bet_type, win_probs, total_runners,
                )
                real_odds = _lookup_real_odds(horse_numbers, bet_type, all_odds)
                ev = prob * real_odds if real_odds > 0 else 0.0
                if _passes_filter(prob, ev):
                    candidates.append(_build_candidate(
                        horse_numbers, bet_type, prob, real_odds, ev, runners_map,
                    ))

        elif bet_type in ("trio", "trifecta"):
            for combo in combinations(eligible, 3):
                horse_numbers = list(combo)
                if bet_type == "trifecta":
                    horse_numbers.sort(key=lambda h: win_probs.get(h, 0), reverse=True)
                prob = _calculate_combination_probability(
                    horse_numbers, bet_type, win_probs, total_runners,
                )
                real_odds = _lookup_real_odds(horse_numbers, bet_type, all_odds)
                ev = prob * real_odds if real_odds > 0 else 0.0
                if _passes_filter(prob, ev):
                    candidates.append(_build_candidate(
                        horse_numbers, bet_type, prob, real_odds, ev, runners_map,
                    ))

    candidates.sort(key=lambda c: c["expected_value"], reverse=True)
    return candidates


def _propose_bets_impl(
    race_id: str,
    win_probabilities: dict[int, float],
    runners_data: list[dict],
    total_runners: int,
    budget: int = 0,
    bankroll: int = 0,
    preferred_bet_types: list[str] | None = None,
    race_name: str = "",
    race_conditions: list[str] | None = None,
    venue: str = "",
    ai_consensus: str = "",
    all_odds: dict | None = None,
) -> dict:
    """EVベース買い目提案の統合実装（テスト用に公開）."""
    race_conditions = race_conditions or []
    runners_map = {int(r.get("horse_number", 0)): r for r in runners_data}
    bet_types = preferred_bet_types or DEFAULT_BET_TYPES

    # budget=0 の場合、好み設定の race_budget をフォールバックとして使う
    if budget == 0 and _current_betting_preference:
        budget = int(_current_betting_preference.get("race_budget", 0))

    use_bankroll = bankroll > 0

    # 0. 実オッズ取得
    if all_odds is None:
        all_odds = _fetch_all_odds(race_id)

    # 1. EV計算+買い目候補生成（フィルタ条件を満たす全候補）
    ev_filter = _resolve_ev_filter(_current_betting_preference)
    bets = _generate_ev_candidates(
        win_probabilities, runners_map, bet_types, total_runners, all_odds,
        ev_filter=ev_filter,
    )

    # 2. 予算計算
    if use_bankroll:
        base_rate = DEFAULT_BASE_RATE
        race_budget = int(bankroll * base_rate)
        race_budget = min(race_budget, int(bankroll * MAX_RACE_BUDGET_RATIO))
        effective_budget = race_budget
    else:
        effective_budget = budget
        race_budget = 0

    # 3. 予算配分
    if bets and effective_budget > 0:
        if use_bankroll:
            bets = _allocate_budget_dutching(bets, effective_budget)
        else:
            bets = _allocate_budget(bets, effective_budget)

    total_amount = sum(b.get("amount", 0) for b in bets)
    budget_remaining = effective_budget - total_amount

    # 4. ナレーション（コスト抑制のため上位10件のみ渡す）
    narration_context = {
        "race_name": race_name,
        "ai_consensus": ai_consensus,
        "bets": bets[:10],
        "runners_data": runners_data,
    }
    analysis_comment = _invoke_haiku_narrator(narration_context)
    if not analysis_comment:
        analysis_comment = f"EV分析に基づく提案。{len(bets)}点。"

    result = {
        "race_id": race_id,
        "race_summary": {
            "race_name": race_name,
            "ai_consensus_level": ai_consensus or "不明",
        },
        "proposed_bets": bets,
        "total_amount": total_amount,
        "budget_remaining": max(0, budget_remaining),
        "analysis_comment": analysis_comment,
        "proposal_reasoning": _build_proposal_reasoning(ev_filter, len(bets)),
        "disclaimer": "この提案はデータ分析に基づくものであり、的中を保証するものではありません。",
    }

    if use_bankroll:
        result["race_budget"] = race_budget
        result["bankroll_usage_pct"] = round(total_amount / bankroll * 100, 2) if bankroll > 0 else 0

    return result


@tool
def propose_bets(
    race_id: str,
    win_probabilities: dict[str, float],
    budget: int = 0,
    bankroll: int = 0,
    preferred_bet_types: list[str] | None = None,
    race_name: str = "",
    race_conditions: list[str] | None = None,
    venue: str = "",
    ai_consensus: str = "",
    runners_data: list[dict] | None = None,
    total_runners: int = 0,
) -> dict:
    """LLMが判断した勝率から期待値を計算し、買い目を提案する。

    analyze_race_for_betting の結果を見てLLMが各馬の勝率を判断した後、
    この関数に勝率を渡す。確率×オッズで期待値(EV)を計算し、
    フィルタ条件（デフォルト EV >= 1.0）を満たす全組合せを買い目として
    選定・予算配分する。

    Args:
        race_id: レースID
        win_probabilities: LLMが判断した勝率 {"1": 0.25, "3": 0.18, ...} 馬番→勝率
        budget: 従来モード予算（円）
        bankroll: bankrollモード総資金（円）
        preferred_bet_types: 券種フィルタ (例: ["quinella", "trio"])
        race_name: レース名（表示用）
        race_conditions: レース条件リスト
        venue: 競馬場名
        ai_consensus: AI合議レベル
        runners_data: 出走馬データ（馬名・オッズ表示用）
        total_runners: 出走頭数

    Returns:
        dict: 買い目提案（race_summary, proposed_bets, total_amount等）
    """
    global _last_ev_proposal_result
    _last_ev_proposal_result = None

    try:
        # win_probabilities のキーを int に変換（LLMが文字列で渡す場合の対応）
        int_probs = {int(k): float(v) for k, v in win_probabilities.items()}

        # 好み設定から preferred_bet_types を解決（LLMが明示指定しなかった場合のみ）
        if preferred_bet_types is None:
            preferred_bet_types = _resolve_bet_types(_current_betting_preference)

        # runners_data が渡されない場合はレースデータから取得
        if not runners_data:
            from .race_data import _fetch_race_detail
            race_detail = _fetch_race_detail(race_id)
            runners_data = race_detail.get("runners", [])
            if total_runners == 0:
                total_runners = race_detail.get("race", {}).get(
                    "horse_count", len(runners_data),
                )

        if total_runners == 0:
            total_runners = len(runners_data)

        result = _propose_bets_impl(
            race_id=race_id,
            win_probabilities=int_probs,
            runners_data=runners_data,
            total_runners=total_runners,
            budget=budget,
            bankroll=bankroll,
            preferred_bet_types=preferred_bet_types,
            race_name=race_name,
            race_conditions=race_conditions,
            venue=venue,
            ai_consensus=ai_consensus,
        )

        _last_ev_proposal_result = result
        return result
    except Exception as e:
        logger.exception("propose_bets failed")
        return {"error": f"買い目提案に失敗しました: {e}"}


def _build_proposal_reasoning(
    ev_filter: tuple[float, float, float | None, float | None],
    bet_count: int,
) -> str:
    """提案理由の文字列を組み立てる."""
    min_prob, min_ev, max_prob, max_ev = ev_filter
    if max_prob is not None:
        prob_part = f"確率{min_prob*100:.0f}〜{max_prob*100:.0f}%"
    else:
        prob_part = f"確率{min_prob*100:.0f}%以上"
    if max_ev is not None:
        ev_part = f"期待値{min_ev:.1f}〜{max_ev:.1f}"
    else:
        ev_part = f"期待値{min_ev:.1f}以上"
    return f"{prob_part}・{ev_part}で{bet_count}点選定"
