"""レース分析ツール.

レースデータを収集し、各馬のベース勝率を算出する。
LLMが買い目判断に使う分析データを提供する。
"""

import logging

from strands import tool

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


@tool
def analyze_race_for_betting(race_id: str) -> dict:
    """レースを分析し、各馬のベース勝率と分析データを返す。

    AI指数（3ソース重み付き統合）、脚質、スピード指数、過去成績を取得し、
    各馬のベース勝率を算出する。LLMはこの結果を見て勝率を調整し、
    propose_bets に渡す。

    Args:
        race_id: レースID (例: "202602010511")

    Returns:
        dict: レース分析結果
            - race_info: レース基本情報（難易度、ペース予想、見送りスコア等）
            - horses: 各馬の情報（ベース勝率、AI指数、脚質、スピード指数、近走成績）
            - source_weights: AI予想ソースの重み
    """
    try:
        from .race_data import _fetch_race_detail, _extract_race_conditions
        from .ai_prediction import get_ai_prediction
        from .pace_analysis import _get_running_styles
        from .speed_index import get_speed_index
        from .past_performance import get_past_performance

        # レースデータ取得
        race_detail = _fetch_race_detail(race_id)
        race = race_detail.get("race", {})
        runners_data = race_detail.get("runners", [])
        race_conditions = _extract_race_conditions(race)

        # AI予想取得
        ai_result = get_ai_prediction(race_id)
        if not isinstance(ai_result, dict) or "error" in ai_result:
            return {"error": f"AI予想の取得に失敗: {ai_result}"}

        # 脚質データ取得
        running_styles = _get_running_styles(race_id)

        # スピード指数取得
        speed_index_data = None
        si_result = get_speed_index(race_id)
        if isinstance(si_result, dict) and "error" not in si_result:
            speed_index_data = si_result

        # 過去成績取得
        past_performance_data = None
        pp_result = get_past_performance(race_id)
        if isinstance(pp_result, dict) and "error" not in pp_result:
            past_performance_data = pp_result

        return _analyze_race_impl(
            race_id=race_id,
            race_name=race.get("race_name", ""),
            venue=race.get("venue", ""),
            distance=race.get("distance", ""),
            surface=race.get("surface", ""),
            total_runners=race.get("horse_count", len(runners_data)),
            race_conditions=race_conditions,
            runners_data=runners_data,
            ai_result=ai_result,
            running_styles=running_styles,
            speed_index_data=speed_index_data,
            past_performance_data=past_performance_data,
        )
    except Exception as e:
        logger.exception("analyze_race_for_betting failed")
        return {"error": f"レース分析に失敗しました: {e}"}


# ペース相性マッピング
PACE_STYLE_COMPAT = {
    "ハイ": {"差し": 1.0, "追込": 1.0, "自在": 0.5, "先行": -0.5, "逃げ": -1.0},
    "ミドル": {"先行": 0.5, "差し": 0.5, "自在": 0.5, "逃げ": 0.0, "追込": 0.0},
    "スロー": {"逃げ": 1.0, "先行": 1.0, "自在": 0.5, "差し": -0.5, "追込": -1.0},
}


def _analyze_race_impl(
    race_id: str,
    race_name: str,
    venue: str,
    distance: str,
    surface: str,
    total_runners: int,
    race_conditions: list[str],
    runners_data: list[dict],
    ai_result: dict,
    running_styles: list[dict] | None = None,
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
    source_weights: dict[str, float] | None = None,
) -> dict:
    """レース分析の実装（テスト用に公開）.

    Args:
        race_id: レースID
        race_name: レース名
        venue: 競馬場名
        distance: 距離
        surface: 馬場
        total_runners: 出走頭数
        race_conditions: レース条件リスト
        runners_data: 出走馬データ
        ai_result: AI予想結果 (sources配列)
        running_styles: 脚質データ
        speed_index_data: スピード指数データ
        past_performance_data: 過去成績データ
        source_weights: AI予想ソース重み

    Returns:
        レース分析結果 (race_info, horses, source_weights)
    """
    from .pace_analysis import _assess_race_difficulty, _predict_pace
    from .risk_analysis import _assess_skip_recommendation
    from .bet_proposal import _calculate_confidence_factor, _assess_ai_consensus

    running_styles = running_styles or []
    weights = source_weights or DEFAULT_SOURCE_WEIGHTS

    # ベース確率算出
    base_probs = _compute_weighted_probabilities(ai_result, weights)

    # ペース予想
    front_runners = sum(1 for rs in running_styles if rs.get("running_style") == "逃げ")
    predicted_pace = _predict_pace(front_runners, total_runners) if running_styles else ""

    # レース難易度
    difficulty = _assess_race_difficulty(total_runners, race_conditions, venue, runners_data)

    # 見送りスコア
    ai_predictions = []
    sources = ai_result.get("sources", [])
    if sources:
        ai_predictions = sources[0].get("predictions", [])
    skip = _assess_skip_recommendation(
        total_runners, race_conditions, venue, runners_data,
        ai_predictions, predicted_pace,
    )
    skip_score = skip.get("skip_score", 0)
    confidence_factor = _calculate_confidence_factor(skip_score)

    # AI合議
    ai_consensus = _assess_ai_consensus(ai_predictions) if ai_predictions else "データなし"

    # 脚質マップ
    style_map = {rs.get("horse_number"): rs.get("running_style", "") for rs in running_styles}

    # スピード指数マップ
    si_map = {}
    if speed_index_data and "horses" in speed_index_data:
        for h in speed_index_data["horses"]:
            hn = h.get("horse_number")
            indices = h.get("indices", [])
            if hn and indices:
                latest = float(indices[0].get("value", 0))
                avg = sum(float(idx.get("value", 0)) for idx in indices) / len(indices)
                si_map[hn] = {"latest": latest, "avg": round(avg, 1)}

    # 過去成績マップ
    pp_map = {}
    if past_performance_data and "horses" in past_performance_data:
        for h in past_performance_data["horses"]:
            hn = h.get("horse_number")
            perfs = h.get("performances", [])
            if hn and perfs:
                form = [int(p.get("finish_position", 99)) for p in perfs[:5]]
                pp_map[hn] = form

    # AI予想スコアマップ（全ソース）
    ai_scores_map: dict[int, dict] = {}
    for source in sources:
        source_name = source.get("source", "")
        for pred in source.get("predictions", []):
            hn = int(pred.get("horse_number", 0))
            score = float(pred.get("score", 0))
            if hn > 0:
                if hn not in ai_scores_map:
                    ai_scores_map[hn] = {}
                ai_scores_map[hn][source_name] = score

    # 各馬の情報を構築
    horses = []
    for runner in runners_data:
        hn = runner.get("horse_number")
        style = style_map.get(hn, "")
        pace_compat = PACE_STYLE_COMPAT.get(predicted_pace, {}).get(style, 0.0)

        horses.append({
            "number": hn,
            "name": runner.get("horse_name", ""),
            "odds": float(runner.get("odds", 0)),
            "base_win_probability": base_probs.get(hn, 0.0),
            "ai_scores": ai_scores_map.get(hn, {}),
            "running_style": style or None,
            "pace_compatibility": pace_compat,
            "speed_index": si_map.get(hn),
            "recent_form": pp_map.get(hn),
        })

    return {
        "race_info": {
            "race_id": race_id,
            "race_name": race_name,
            "venue": venue,
            "distance": distance,
            "surface": surface,
            "total_runners": total_runners,
            "difficulty": difficulty,
            "predicted_pace": predicted_pace,
            "skip_score": skip_score,
            "ai_consensus": ai_consensus,
            "confidence_factor": confidence_factor,
        },
        "horses": horses,
        "source_weights": weights,
    }
