"""バックテスト確定済みの確率推定パイプライン.

optimize_staking.py (backtest) の関数群を完全再現。
定数・計算ロジックを一切変更しないこと。
"""
import math

SOURCES = ["keiba-ai-navi", "umamax", "muryou-keiba-ai", "keiba-ai-athena"]

BETAS = {
    "umamax": 0.052082,
    "muryou-keiba-ai": 0.072791,
    "keiba-ai-athena": 0.006745,
    "keiba-ai-navi": 0.070031,
}

# MLE最適化ウェイト（SOURCES順: navi, umamax, muryou, athena）
WIN_WEIGHTS = [0.401, 0.035, 0.251, 0.313]
PLACE_WEIGHTS = [0.314, 0.214, 0.309, 0.164]


def softmax(scores: list, beta: float) -> list[float]:
    """Softmax calibration."""
    max_s = max(scores)
    exps = [math.exp(beta * (s - max_s)) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def source_to_probs(preds: list[dict], beta: float) -> dict[int, float]:
    """ソース予想をSoftmax確率に変換."""
    scores = [p["score"] for p in preds]
    horse_nums = [p["horse_number"] for p in preds]
    return dict(zip(horse_nums, softmax(scores, beta)))


def log_opinion_pool(
    prob_dicts: list[dict[int, float]], weights: list[float]
) -> dict[int, float]:
    """Log Opinion Poolで複数ソースの確率を統合."""
    all_horses = set(prob_dicts[0].keys())
    for pd in prob_dicts[1:]:
        all_horses &= set(pd.keys())
    if not all_horses:
        return {}
    combined = {}
    for h in all_horses:
        log_p = sum(
            w * math.log(max(pd.get(h, 1e-10), 1e-10))
            for pd, w in zip(prob_dicts, weights)
        )
        combined[h] = math.exp(log_p)
    total = sum(combined.values())
    return {h: p / total for h, p in combined.items()} if total > 0 else {}


def market_implied_probs(odds_win: dict) -> dict[int, float]:
    """単勝オッズからMarket Implied Probabilitiesを算出.

    JRA-VAN APIの単勝オッズはフラットなfloat: {"1": 14.9, "2": 5.0}
    """
    raw = {}
    for hn_str, odds_val in odds_win.items():
        if odds_val > 0:
            raw[int(hn_str)] = 1.0 / odds_val
    total = sum(raw.values())
    return {h: p / total for h, p in raw.items()} if total > 0 else {}


def compute_agree_counts(
    source_probs: list[dict[int, float]], top_n: int
) -> dict[int, int]:
    """各馬番が何ソースのTopN以内にランクされるかを計算."""
    counts: dict[int, int] = {}
    for probs in source_probs:
        ranked = sorted(probs.keys(), key=lambda h: probs[h], reverse=True)[:top_n]
        for h in ranked:
            counts[h] = counts.get(h, 0) + 1
    return counts
