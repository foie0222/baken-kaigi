"""レース分析ツール.

レースデータを収集し、各馬のベース勝率を算出する。
LLMが買い目判断に使う分析データを提供する。
"""

import logging

logger = logging.getLogger(__name__)

# ソースごとのデフォルト重み
DEFAULT_SOURCE_WEIGHTS = {
    "jiro8": 0.40,
    "kichiuma": 0.35,
    "daily": 0.25,
}


def _compute_weighted_probabilities(
    ai_result: dict,
    source_weights: dict[str, float] | None = None,
) -> dict[int, float]:
    """AIソースのスコアを重み付きで統合して馬ごとの勝率を算出する.

    各ソース内でスコアを正規化（score / sum(scores) -> 確率）し、
    ソースの重みで加重平均を取り、再正規化して合計1.0にする。

    Args:
        ai_result: AI予想結果 (sources: [{source, predictions: [{horse_number, score}]}])
        source_weights: ソース名->重みの辞書。Noneの場合はDEFAULT_SOURCE_WEIGHTS

    Returns:
        {horse_number: win_probability} （合計 ≈ 1.0）
    """
    weights = source_weights or DEFAULT_SOURCE_WEIGHTS
    sources = ai_result.get("sources", [])
    if not sources:
        return {}

    # 馬番ごとに重み付き確率を蓄積
    horse_weighted_sum: dict[int, float] = {}
    total_weight_used = 0.0

    for source in sources:
        source_name = source.get("source", "")
        predictions = source.get("predictions", [])
        if not predictions:
            continue

        # ソース内の合計スコア
        scores: dict[int, float] = {}
        for pred in predictions:
            hn = int(pred.get("horse_number", 0))
            score = float(pred.get("score", 0))
            if hn > 0:
                scores[hn] = score

        total_score = sum(scores.values())
        if total_score <= 0:
            continue

        # このソースの重み（未知のソースは均等配分）
        w = weights.get(source_name, 1.0 / max(len(sources), 1))
        total_weight_used += w

        # ソース内正規化 x 重み
        for hn, score in scores.items():
            prob = score / total_score
            horse_weighted_sum[hn] = horse_weighted_sum.get(hn, 0.0) + prob * w

    if not horse_weighted_sum or total_weight_used <= 0:
        return {}

    # 最終正規化（合計=1.0を保証）
    total = sum(horse_weighted_sum.values())
    if total <= 0:
        return {}

    return {hn: p / total for hn, p in horse_weighted_sum.items()}
