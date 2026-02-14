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
    _harville_exacta,
    _harville_trifecta,
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

# セッション単位の好み設定（invoke() から注入される）
_current_betting_preference: dict | None = None


def set_betting_preference(preference: dict | None) -> None:
    """セッションの好み設定を設定する（invoke()から呼ばれる）."""
    global _current_betting_preference
    _current_betting_preference = preference


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
WEIGHT_SPEED_INDEX = 0.20
WEIGHT_FORM = 0.15

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

# 買い目のデフォルト最大数（budgetモード用。bankrollモードでは使用しない）
MAX_BETS = 8

# 最低掛け金
MIN_BET_AMOUNT = 100

# 軸馬の最大数
MAX_AXIS_HORSES = 2

# 1レースあたりの予算上限（bankrollに対する割合）
MAX_RACE_BUDGET_RATIO = 0.10

# デフォルト基本投入率
DEFAULT_BASE_RATE = 0.03


def _calculate_confidence_factor(skip_score: int) -> float:
    """見送りスコアから信頼度係数を算出する.

    見送りスコア(0-10)を0.0-2.0の連続値にマッピング。
    スコア9以上は見送り（0.0）。

    Args:
        skip_score: 見送りスコア（0-10）

    Returns:
        信頼度係数（0.0-2.0）
    """
    if skip_score >= 9:
        return 0.0
    return max(0.0, 2.0 - skip_score * (1.75 / 8))


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

# 着順→スコアのマッピング（近走フォーム用）
FINISH_POSITION_SCORES = {1: 100, 2: 85, 3: 70, 4: 55, 5: 45}
# 6-9着=30, 10着以降=15 は _finish_position_to_score で処理

# 近走重み（最新=5, 2走前=4, ... 5走前=1）
FORM_RECENCY_WEIGHTS = [5, 4, 3, 2, 1]

# ペルソナ別プロファイル
# analyst はデフォルトと同一のため空辞書
CHARACTER_PROFILES = {
    "analyst": {},
    "intuition": {
        "weight_ai_score": 0.3, "weight_odds_gap": 0.5,
        "allocation_high": 0.40, "allocation_low": 0.30,
        "torigami_threshold": 1.5, "skip_gate_threshold": 8,
        "difficulty_bet_types": {
            1: ["exacta", "quinella"], 2: ["exacta", "quinella"],
            3: ["exacta", "trio"], 4: ["trio", "trifecta"],
            5: ["trio", "quinella_place"],
        },
    },
    "conservative": {
        "allocation_high": 0.60, "allocation_low": 0.10,
        "max_bets": 5, "torigami_threshold": 2.5, "skip_gate_threshold": 6,
        "weight_ai_score": 0.6, "weight_odds_gap": 0.2,
        "base_rate": 0.02,
        "difficulty_bet_types": {
            1: ["quinella", "quinella_place"], 2: ["quinella", "quinella_place"],
            3: ["quinella_place", "quinella"], 4: ["quinella_place"],
            5: ["quinella_place"],
        },
    },
    "aggressive": {
        "allocation_high": 0.35, "allocation_medium": 0.25, "allocation_low": 0.40,
        "torigami_threshold": 1.5, "skip_gate_threshold": 9,
        "weight_ai_score": 0.3, "weight_odds_gap": 0.5,
        "base_rate": 0.05,
        "difficulty_bet_types": {
            1: ["exacta", "trifecta"], 2: ["exacta", "trifecta"],
            3: ["trifecta", "trio"], 4: ["trifecta", "trio"],
            5: ["trio", "trifecta"],
        },
    },
}

_DEFAULT_CONFIG = {
    "weight_ai_score": WEIGHT_AI_SCORE, "weight_odds_gap": WEIGHT_ODDS_GAP,
    "weight_pace_compat": WEIGHT_PACE_COMPAT,
    "weight_speed_index": WEIGHT_SPEED_INDEX, "weight_form": WEIGHT_FORM,
    "allocation_high": ALLOCATION_HIGH, "allocation_medium": ALLOCATION_MEDIUM,
    "allocation_low": ALLOCATION_LOW,
    "max_bets": MAX_BETS, "torigami_threshold": TORIGAMI_COMPOSITE_ODDS_THRESHOLD,
    "skip_gate_threshold": SKIP_GATE_THRESHOLD,
    "difficulty_bet_types": DIFFICULTY_BET_TYPES,
    "base_rate": DEFAULT_BASE_RATE,
    "max_partners": MAX_PARTNERS,
}


def _get_character_config(character_type: str | None) -> dict:
    """ペルソナに応じた設定を返す.

    Args:
        character_type: ペルソナ種別（None or 未知のキーはデフォルト）

    Returns:
        設定辞書
    """
    config = dict(_DEFAULT_CONFIG)
    if character_type and character_type in CHARACTER_PROFILES:
        config.update(CHARACTER_PROFILES[character_type])
    return config


# =============================================================================
# 好み設定（BettingPreference）反映
# =============================================================================

# target_style → 難易度券種マッピングのシフト
TARGET_STYLE_DIFFICULTY_BET_TYPES = {
    "honmei": {
        1: ["quinella", "quinella_place"],
        2: ["quinella", "quinella_place"],
        3: ["quinella", "exacta"],
        4: ["quinella", "quinella_place"],
        5: ["quinella_place"],
    },
    "big_longshot": {
        1: ["exacta", "trio"],
        2: ["exacta", "trio"],
        3: ["trio", "trifecta"],
        4: ["trio", "trifecta"],
        5: ["trio", "quinella_place"],
    },
}

# bet_type_preference → 券種候補のオーバーライド
BET_TYPE_PREFERENCE_MAP = {
    "trio_focused": {
        1: ["trio", "exacta"],
        2: ["trio", "exacta"],
        3: ["trio", "trifecta"],
        4: ["trio", "trifecta"],
        5: ["trio", "quinella_place"],
    },
    "exacta_focused": {
        1: ["exacta", "quinella"],
        2: ["exacta", "quinella"],
        3: ["exacta", "trio"],
        4: ["exacta", "trio"],
        5: ["quinella", "quinella_place"],
    },
    "quinella_focused": {
        1: ["quinella", "quinella_place"],
        2: ["quinella", "quinella_place"],
        3: ["quinella", "quinella_place"],
        4: ["quinella_place", "quinella"],
        5: ["quinella_place"],
    },
    "wide_focused": {
        1: ["quinella_place", "quinella"],
        2: ["quinella_place", "quinella"],
        3: ["quinella_place", "quinella"],
        4: ["quinella_place"],
        5: ["quinella_place"],
    },
}

# priority → 相手馬数・軸馬閾値
PRIORITY_WEIGHTS = {
    "hit_rate": {"max_partners": 5},
    "roi": {"max_partners": 3},
    "balanced": {"max_partners": MAX_PARTNERS},
}


def _get_preference_config(
    character_type: str | None,
    betting_preference: dict | None,
) -> dict:
    """ペルソナ設定に好み設定を上書きした設定を返す.

    Args:
        character_type: ペルソナ種別
        betting_preference: 好み設定辞書（bet_type_preference, target_style, priority）

    Returns:
        設定辞書
    """
    config = _get_character_config(character_type)

    if not betting_preference:
        return config

    # priority → max_partners の上書き
    priority = betting_preference.get("priority")
    if priority and priority in PRIORITY_WEIGHTS:
        config.update(PRIORITY_WEIGHTS[priority])

    # bet_type_preference → difficulty_bet_types の上書き
    bet_type_pref = betting_preference.get("bet_type_preference")
    if bet_type_pref and bet_type_pref != "auto" and bet_type_pref in BET_TYPE_PREFERENCE_MAP:
        config["difficulty_bet_types"] = dict(BET_TYPE_PREFERENCE_MAP[bet_type_pref])
    else:
        # target_style → difficulty_bet_types のシフト（bet_type_preferenceが auto の場合のみ）
        target_style = betting_preference.get("target_style")
        if target_style and target_style in TARGET_STYLE_DIFFICULTY_BET_TYPES:
            config["difficulty_bet_types"] = dict(TARGET_STYLE_DIFFICULTY_BET_TYPES[target_style])

    return config


# =============================================================================
# スピード指数・近走フォームスコア
# =============================================================================


def _calculate_speed_index_score(
    horse_number: int,
    speed_index_data: dict | None,
) -> float | None:
    """スピード指数から馬ごとのスコアを計算する.

    複数ソースの指数を馬ごとに平均し、レース内順位で0-100にスケーリングする。

    Args:
        horse_number: 馬番
        speed_index_data: get_speed_index の結果（sources を含む辞書）

    Returns:
        スコア（0-100）。データなしの場合は None。
    """
    if not speed_index_data:
        return None

    sources = speed_index_data.get("sources", [])
    if not sources:
        return None

    # 馬番ごとにスピード指数を収集
    horse_indices: dict[int, list[float]] = {}
    for source in sources:
        for idx in source.get("indices", []):
            hn = int(idx.get("horse_number", 0))
            si = idx.get("speed_index")
            if si is not None:
                horse_indices.setdefault(hn, []).append(float(si))

    if horse_number not in horse_indices:
        return None

    # 各馬の平均指数を計算
    averages = {hn: sum(vals) / len(vals) for hn, vals in horse_indices.items()}

    # 平均指数で降順ソートしてランク付け
    ranked = sorted(averages.items(), key=lambda x: -x[1])
    n = len(ranked)

    rank = None
    for i, (hn, _) in enumerate(ranked, 1):
        if hn == horse_number:
            rank = i
            break

    if rank is None:
        return None

    # スケーリング: 1位=100, 最下位=15
    if n == 1:
        return 100.0
    score = 100.0 - (rank - 1) * 85.0 / (n - 1)
    return round(score, 1)


def _finish_position_to_score(pos: int) -> float:
    """着順をスコアに変換する."""
    if pos in FINISH_POSITION_SCORES:
        return float(FINISH_POSITION_SCORES[pos])
    elif 6 <= pos <= 9:
        return 30.0
    else:
        return 15.0


def _calculate_form_score(
    horse_number: int,
    past_performance_data: dict | None,
) -> float | None:
    """近走成績からフォームスコアを計算する.

    直近5走の着順をスコア化し、近走ほど重みを大きくして加重平均を計算する。

    Args:
        horse_number: 馬番
        past_performance_data: get_past_performance の結果（sources を含む辞書）

    Returns:
        スコア（0-100）。データなしの場合は None。
    """
    if not past_performance_data:
        return None

    sources = past_performance_data.get("sources", [])
    if not sources:
        return None

    # 全ソースから該当馬の過去成績を探す（最初に見つかったものを使用）
    past_races = None
    for source in sources:
        for horse in source.get("horses", []):
            if int(horse.get("horse_number", 0)) == horse_number:
                past_races = horse.get("past_races", [])
                break
        if past_races is not None:
            break

    if not past_races:
        return None

    # 直近5走まで
    recent = past_races[:5]

    total_weighted_score = 0.0
    total_weight = 0.0
    for i, race in enumerate(recent):
        pos = int(race.get("finish_position", 99))
        score = _finish_position_to_score(pos)
        weight = FORM_RECENCY_WEIGHTS[i]
        total_weighted_score += score * weight
        total_weight += weight

    if total_weight == 0:
        return None

    return round(total_weighted_score / total_weight, 1)


# =============================================================================
# Phase 2: 軸馬選定
# =============================================================================


def _calculate_composite_score(
    horse_number: int,
    runners_data: list[dict],
    ai_predictions: list[dict],
    predicted_pace: str = "",
    running_styles: list[dict] | None = None,
    weight_ai_score: float = WEIGHT_AI_SCORE,
    weight_odds_gap: float = WEIGHT_ODDS_GAP,
    weight_pace_compat: float = WEIGHT_PACE_COMPAT,
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
    weight_speed_index: float = WEIGHT_SPEED_INDEX,
    weight_form: float = WEIGHT_FORM,
    unified_probs: dict[int, float] | None = None,
) -> float:
    """AI指数順位 x オッズ乖離 x 展開相性 (+ スピード指数 + 近走フォーム) の複合スコアを計算する.

    データがある成分のみ動的に重み再正規化を行い、
    データなし時は既存3成分と完全同一の結果を返す。

    Args:
        horse_number: 馬番
        runners_data: 出走馬データ
        ai_predictions: AI予想データ
        predicted_pace: 予想ペース
        running_styles: 脚質データ
        speed_index_data: スピード指数データ（Noneなら無視）
        past_performance_data: 過去成績データ（Noneなら無視）

    Returns:
        複合スコア（0-100）
    """
    running_styles = running_styles or []

    # AI順位スコア（1位=100, 2位=90, ...）
    ai_score = 0.0
    ai_rank = 99
    if unified_probs:
        # 統合確率から順位を再計算
        sorted_probs = sorted(unified_probs.items(), key=lambda x: x[1], reverse=True)
        rank_map = {hn: i + 1 for i, (hn, _) in enumerate(sorted_probs)}
        ai_rank = rank_map.get(horse_number, 99)
        ai_score = max(0.0, 100.0 - (ai_rank - 1) * 5.0)
    else:
        for pred in ai_predictions:
            if int(pred.get("horse_number", 0)) == horse_number:
                ai_rank = int(pred.get("rank", 99))
                ai_score = max(0.0, 100.0 - (ai_rank - 1) * 5.0)
                break

    # オッズ乖離スコア
    odds_gap_score = 50.0  # デフォルト（データ不足時）
    runner = next((r for r in runners_data if r.get("horse_number") == horse_number), None)
    if runner:
        popularity = runner.get("popularity")
        if popularity and popularity > 0:
            # 人気データがある場合のみ乖離スコアを計算
            if ai_rank <= ODDS_GAP_BONUS_THRESHOLD and popularity > ODDS_GAP_BONUS_THRESHOLD:
                odds_gap_score = min(100.0, 80.0 + (popularity - ai_rank) * 2)
            elif ai_rank <= 3 and popularity <= 3:
                odds_gap_score = 60.0  # 順当
            elif ai_rank > ODDS_GAP_BONUS_THRESHOLD and popularity <= 3:
                odds_gap_score = 20.0  # 過剰人気
            else:
                odds_gap_score = 50.0
        # 人気データがない場合はデフォルト50.0のまま（不確実性を反映）

    # 展開相性スコア
    # 脚質データがない場合は不確実性ペナルティを適用
    pace_score = 40.0 if (not predicted_pace or not running_styles) else 50.0
    if predicted_pace and running_styles:
        style_map = {r.get("horse_number"): r.get("running_style", "不明") for r in running_styles}
        style = style_map.get(horse_number, "不明")
        compat = PACE_STYLE_COMPAT.get(predicted_pace, {})
        pace_value = compat.get(style, 0.0)
        pace_score = 50.0 + pace_value * 25.0  # -1.0~1.0 -> 25~75

    # 動的重み正規化: データがある成分のみ使用
    components = [
        (ai_score, weight_ai_score),
        (odds_gap_score, weight_odds_gap),
        (pace_score, weight_pace_compat),
    ]
    speed_score = _calculate_speed_index_score(horse_number, speed_index_data)
    if speed_score is not None:
        components.append((speed_score, weight_speed_index))
    form_score = _calculate_form_score(horse_number, past_performance_data)
    if form_score is not None:
        components.append((form_score, weight_form))

    total_weight = sum(w for _, w in components)
    composite = sum(s * (w / total_weight) for s, w in components)
    return round(min(100, max(0, composite)), 1)


def _select_axis_horses(
    runners_data: list[dict],
    ai_predictions: list[dict],
    predicted_pace: str = "",
    running_styles: list[dict] | None = None,
    user_axis: list[int] | None = None,
    weight_ai_score: float = WEIGHT_AI_SCORE,
    weight_odds_gap: float = WEIGHT_ODDS_GAP,
    weight_pace_compat: float = WEIGHT_PACE_COMPAT,
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
    weight_speed_index: float = WEIGHT_SPEED_INDEX,
    weight_form: float = WEIGHT_FORM,
    unified_probs: dict[int, float] | None = None,
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
                    hn, runners_data, ai_predictions, predicted_pace, running_styles,
                    weight_ai_score=weight_ai_score, weight_odds_gap=weight_odds_gap,
                    weight_pace_compat=weight_pace_compat,
                    speed_index_data=speed_index_data,
                    past_performance_data=past_performance_data,
                    weight_speed_index=weight_speed_index,
                    weight_form=weight_form,
                    unified_probs=unified_probs,
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
            hn, runners_data, ai_predictions, predicted_pace, running_styles,
            weight_ai_score=weight_ai_score, weight_odds_gap=weight_odds_gap,
            weight_pace_compat=weight_pace_compat,
            speed_index_data=speed_index_data,
            past_performance_data=past_performance_data,
            weight_speed_index=weight_speed_index,
            weight_form=weight_form,
            unified_probs=unified_probs,
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
    difficulty_bet_types: dict | None = None,
) -> list[str]:
    """レース難易度から推奨券種を選定する.

    Args:
        difficulty_stars: レース難易度（1-5）
        preferred_bet_types: ユーザー指定の券種リスト
        difficulty_bet_types: ペルソナ別の難易度→券種マッピング

    Returns:
        推奨券種リスト
    """
    if preferred_bet_types:
        return preferred_bet_types

    mapping = difficulty_bet_types if difficulty_bet_types is not None else DIFFICULTY_BET_TYPES
    stars = max(1, min(5, difficulty_stars))
    return mapping[stars]


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


def _assign_relative_confidence(bets: list[dict]) -> None:
    """候補リスト内のスコア分布に基づいて信頼度を相対的に割り当てる.

    絶対閾値（>=70で「高」等）ではなく、
    選ばれた候補内での相対順位で信頼度を決める。
    これにより候補間で信頼度にばらつきが出る。

    割り当て規則:
        - 1件: "high"
        - 2件: 上位 "high", 下位 "medium"
        - 3件以上: 上位1/3 "high", 中位 "medium", 下位1/3 "low"
        - 全スコア同値: expected_valueで代替ランク付け
        - 全スコア・期待値ともに同値: 全て "medium"

    Args:
        bets: 買い目候補リスト（_composite_scoreキーを持つ）。
              スコア同値時はexpected_valueキーをフォールバックに使用。
              リストをin-placeで変更する。
    """
    n = len(bets)
    if n == 0:
        return
    if n == 1:
        bets[0]["confidence"] = "high"
        return

    scores = [b.get("_composite_score", 0) for b in bets]
    if max(scores) == min(scores):
        # スコア同値の場合、期待値でフォールバック
        ev_scores = [b.get("expected_value", 0) for b in bets]
        if max(ev_scores) == min(ev_scores):
            for b in bets:
                b["confidence"] = "medium"
            return
        scores = ev_scores

    # スコア降順でランク付け
    indexed = sorted(range(n), key=lambda i: scores[i], reverse=True)

    if n == 2:
        bets[indexed[0]]["confidence"] = "high"
        bets[indexed[1]]["confidence"] = "medium"
        return

    # 3件以上: 上位1/3, 中位, 下位1/3
    high_count = max(1, round(n / 3))
    # medium は残り（最低0）、low は残りの要素数
    medium_count = n - high_count - max(1, round(n / 3))
    if medium_count < 0:
        # n=3で high_count=1 → lowも1、medium=1 となるため通常は到達しない
        high_count = 1
        medium_count = n - 2

    for rank, idx in enumerate(indexed):
        if rank < high_count:
            bets[idx]["confidence"] = "high"
        elif rank < high_count + medium_count:
            bets[idx]["confidence"] = "medium"
        else:
            bets[idx]["confidence"] = "low"


def _generate_bet_candidates(
    axis_horses: list[dict],
    runners_data: list[dict],
    ai_predictions: list[dict],
    bet_types: list[str],
    total_runners: int,
    race_conditions: list[str] | None = None,
    predicted_pace: str = "",
    running_styles: list[dict] | None = None,
    max_bets: int | None = None,
    torigami_threshold: float = TORIGAMI_COMPOSITE_ODDS_THRESHOLD,
    weight_ai_score: float = WEIGHT_AI_SCORE,
    weight_odds_gap: float = WEIGHT_ODDS_GAP,
    weight_pace_compat: float = WEIGHT_PACE_COMPAT,
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
    weight_speed_index: float = WEIGHT_SPEED_INDEX,
    weight_form: float = WEIGHT_FORM,
    unified_probs: dict[int, float] | None = None,
    max_partners: int = MAX_PARTNERS,
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
            hn, runners_data, ai_predictions, predicted_pace, running_styles,
            weight_ai_score=weight_ai_score, weight_odds_gap=weight_odds_gap,
            weight_pace_compat=weight_pace_compat,
            speed_index_data=speed_index_data,
            past_performance_data=past_performance_data,
            weight_speed_index=weight_speed_index,
            weight_form=weight_form,
            unified_probs=unified_probs,
        )
        partner_scores.append({
            "horse_number": hn,
            "composite_score": score,
        })
    partner_scores.sort(key=lambda x: x["composite_score"], reverse=True)
    partners = partner_scores[:max_partners]

    bets = []
    for bet_type in bet_types:
        # 単勝/複勝は軸馬のみで買い目生成（相手馬不要）
        if bet_type in ("win", "place"):
            for axis in axis_horses:
                axis_hn = axis["horse_number"]
                axis_runner = runners_map.get(axis_hn, {})
                axis_pop = axis_runner.get("popularity") or 0
                axis_odds = axis_runner.get("odds") or 0

                if unified_probs:
                    ev = _calculate_combination_ev(
                        [axis_hn], bet_type, axis_odds,
                        unified_probs, total_runners,
                    )
                    ev["expected_return"] = ev.pop("expected_return", 0)
                else:
                    ev = _calculate_expected_value(
                        axis_odds, axis_pop, bet_type, total_runners, race_conditions
                    )

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
                    "confidence": "medium",
                    "_composite_score": axis["composite_score"],
                    "expected_value": ev.get("expected_return", 0),
                    "composite_odds": axis_odds,
                    "composite_score": axis["composite_score"],
                    "reasoning": reasoning,
                    "bet_count": 1,
                })
            continue


        for axis in axis_horses:
            axis_hn = axis["horse_number"]
            axis_runner = runners_map.get(axis_hn, {})
            axis_pop = axis_runner.get("popularity") or 0
            axis_odds = axis_runner.get("odds") or 0

            for partner in partners:
                partner_hn = partner["horse_number"]
                partner_runner = runners_map.get(partner_hn, {})
                partner_pop = partner_runner.get("popularity") or 0
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

                # 期待値計算
                if unified_probs:
                    ev = _calculate_combination_ev(
                        horse_numbers, bet_type, estimated_odds,
                        unified_probs, total_runners,
                    )
                    ev["expected_return"] = ev.pop("expected_return", 0)
                else:
                    known_pops = [p for p in [axis_pop, partner_pop] if p > 0]
                    avg_pop = sum(known_pops) // len(known_pops) if known_pops else 0
                    ev = _calculate_expected_value(
                        estimated_odds, avg_pop, bet_type, total_runners, race_conditions
                    )

                # トリガミチェック（推定オッズが閾値未満なら除外）
                if 0 < estimated_odds < torigami_threshold:
                    continue  # トリガミ除外

                # reasoning生成
                avg_score = round((axis["composite_score"] + partner["composite_score"]) / 2, 1)
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
                    "confidence": "medium",
                    "_composite_score": avg_score,
                    "expected_value": ev.get("expected_return", 0),
                    "composite_odds": estimated_odds,
                    "composite_score": avg_score,
                    "reasoning": reasoning,
                    "bet_count": 1,
                })

        # 3連系の処理
        if bet_type in ("trio", "trifecta") and len(partners) >= 2:
            from itertools import combinations as combs

            for axis in axis_horses:
                axis_hn = axis["horse_number"]
                axis_runner = runners_map.get(axis_hn, {})
                axis_pop = axis_runner.get("popularity") or 0
                axis_odds = axis_runner.get("odds") or 0

                for p1, p2 in combs(partners[:max_partners], 2):
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

                    p1_pop = p1_runner.get("popularity") or 0
                    p2_pop = p2_runner.get("popularity") or 0

                    # 推定オッズ（券種別補正係数を適用）
                    estimated_odds = _estimate_bet_odds(
                        [axis_odds, p1_odds, p2_odds], bet_type
                    )

                    # 期待値計算
                    if unified_probs:
                        ev = _calculate_combination_ev(
                            horse_numbers, bet_type, estimated_odds,
                            unified_probs, total_runners,
                        )
                        ev["expected_return"] = ev.pop("expected_return", 0)
                    else:
                        known_pops = [p for p in [axis_pop, p1_pop, p2_pop] if p > 0]
                        avg_pop = sum(known_pops) // len(known_pops) if known_pops else 0
                        ev = _calculate_expected_value(
                            estimated_odds, avg_pop, bet_type, total_runners, race_conditions
                        )

                    # トリガミチェック
                    if 0 < estimated_odds < TORIGAMI_COMPOSITE_ODDS_THRESHOLD:
                        continue

                    avg_score = round((axis["composite_score"] + p1["composite_score"] + p2["composite_score"]) / 3, 1)

                    reasoning = f"{axis_hn}番軸-{p1_hn}番-{p2_hn}番の{BET_TYPE_NAMES.get(bet_type, bet_type)}"

                    bets.append({
                        "bet_type": bet_type,
                        "bet_type_name": BET_TYPE_NAMES.get(bet_type, bet_type),
                        "horse_numbers": horse_numbers,
                        "bet_display": bet_display,
                        "confidence": "medium",
                        "_composite_score": avg_score,
                        "expected_value": ev.get("expected_return", 0),
                        "composite_odds": estimated_odds,
                        "composite_score": avg_score,
                        "reasoning": reasoning,
                        "bet_count": 1,
                    })

    # 期待値降順ソート
    bets.sort(key=lambda x: x["expected_value"], reverse=True)
    if max_bets is not None:
        selected = bets[:max_bets]
    else:
        selected = bets

    # 信頼度を候補リスト内のスコア分布に基づいて相対的に再割り当て
    _assign_relative_confidence(selected)

    # 内部スコアはソート専用のため、ユーザー向けレスポンスからは削除する
    for bet in selected:
        bet.pop("_composite_score", None)

    return selected


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
    allocation_high: float = ALLOCATION_HIGH,
    allocation_medium: float = ALLOCATION_MEDIUM,
    allocation_low: float = ALLOCATION_LOW,
) -> list[dict]:
    """信頼度別に予算を配分する.

    100円単位に丸め、最低100円保証。

    Args:
        bets: 買い目候補リスト
        budget: 総予算
        allocation_high: 高信頼の配分比率
        allocation_medium: 中信頼の配分比率
        allocation_low: 穴狙いの配分比率

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
        groups.append(("high", high, allocation_high))
    if medium:
        groups.append(("medium", medium, allocation_medium))
    if value:
        groups.append(("low", value, allocation_low))

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
            groups.append(("high", high, allocation_high))
        if medium:
            groups.append(("medium", medium, allocation_medium))
        if value:
            groups.append(("low", value, allocation_low))
        if not groups:
            return bets

    # 比率を正規化
    total_ratio = sum(g[2] for g in groups)
    normalized = [(g[0], g[1], g[2] / total_ratio) for g in groups]

    unit = MIN_BET_AMOUNT  # 丸め単位（100円）

    total_amount = 0
    for _, group_bets, ratio in normalized:
        group_budget = int(budget * ratio)
        # 期待値ベースの傾斜配分
        evs = [max(0, b.get("expected_value", 0)) for b in group_bets]
        total_ev = sum(evs)
        if total_ev > 0:
            # 期待値に比例して配分（unit単位に丸め、最低unit保証）
            for i, bet in enumerate(group_bets):
                raw = group_budget * evs[i] / total_ev
                bet["amount"] = max(unit, int(math.floor(raw / unit) * unit))
                total_amount += bet["amount"]
        else:
            # 期待値が全て0の場合は均等配分
            per_bet = max(unit, int(math.floor(group_budget / len(group_bets) / unit) * unit))
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
            reducible = b["amount"] - unit
            if reducible > 0:
                reduction = min(reducible, overage)
                reduction = (reduction // unit) * unit
                if reduction > 0:
                    b["amount"] -= reduction
                    overage -= reduction

    # 余剰予算を期待値比率で追加配分
    remaining = budget - sum(b.get("amount", 0) for b in bets if "amount" in b)
    if remaining >= unit:
        positive_ev_bets = [
            b for b in bets
            if "amount" in b and b.get("expected_value", 0) > 0
        ]

        if positive_ev_bets:
            # EV比率に応じて余剰を配分（unit単位に丸め）
            sorted_by_ev = sorted(
                positive_ev_bets,
                key=lambda b: b.get("expected_value", 0),
                reverse=True,
            )
            total_positive_ev = sum(b.get("expected_value", 0) for b in positive_ev_bets)
            initial_remaining = remaining
            for bet in sorted_by_ev:
                ev = bet.get("expected_value", 0)
                add = int(math.floor(initial_remaining * ev / total_positive_ev / unit) * unit)
                add = min(add, remaining)
                if add >= unit:
                    bet["amount"] += add
                    remaining -= add
            # 丸め残りはEV最大の買い目に追加
            if remaining >= unit:
                top_add = int(remaining // unit) * unit
                sorted_by_ev[0]["amount"] += top_add
                remaining -= top_add
        else:
            # 全EV=0: 均等に追加配分
            all_bets = [b for b in bets if "amount" in b]
            while remaining >= unit:
                for bet in all_bets:
                    if remaining < unit:
                        break
                    bet["amount"] += unit
                    remaining -= unit

    return bets


def _allocate_budget_dutching(bets: list[dict], budget: int) -> list[dict]:
    """ダッチング方式で予算を配分する.

    どの買い目が的中しても同額の払い戻しになるように、
    オッズの逆数に比例して配分する。

    Args:
        bets: 買い目候補リスト（composite_odds, expected_value キーを持つ）
        budget: 総予算（円）

    Returns:
        金額付き買い目リスト（期待値>1.0のもののみ）。
        betsが空またはbudget<=0の場合はそのまま返す。
    """
    if not bets or budget <= 0:
        return bets

    eligible = [b for b in bets if b.get("expected_value", 0) > 1.0]
    if not eligible:
        return []

    inv_odds_sum = sum(1.0 / float(b["composite_odds"]) for b in eligible)
    composite_odds = 1.0 / inv_odds_sum

    unit = MIN_BET_AMOUNT
    for bet in eligible:
        raw = budget * composite_odds / float(bet["composite_odds"])
        bet["amount"] = max(unit, int(math.floor(raw / unit) * unit))

    funded = [b for b in eligible if b.get("amount", 0) >= unit]

    # 合計が予算を超える場合、配分額が最小の買い目を除外して再帰
    total = sum(b["amount"] for b in funded)
    if total > budget and len(funded) > 1:
        funded.sort(key=lambda x: x["amount"])
        return _allocate_budget_dutching(funded[1:], budget)

    if len(funded) < len(eligible):
        return _allocate_budget_dutching(funded, budget)

    remaining = budget - total
    if remaining >= unit and funded:
        funded[0]["amount"] += int(remaining // unit) * unit

    final_inv_sum = sum(1.0 / float(b["composite_odds"]) for b in funded)
    final_composite = round(1.0 / final_inv_sum, 2) if final_inv_sum > 0 else 0
    for bet in funded:
        bet["dutching_composite_odds"] = final_composite

    return funded


# =============================================================================
# Phase 6: AI合議レベル判定
# =============================================================================


def _assess_ai_consensus(
    ai_predictions: list[dict],
    unified_probs: dict[int, float] | None = None,
) -> str:
    """AI予想の合議レベルを判定する.

    unified_probsがある場合は統合確率の上位2頭の確率差で判定し、
    ない場合は単一ソースのスコア差で判定する。

    Args:
        ai_predictions: AI予想データ
        unified_probs: 統合単勝率（Noneなら従来ロジック）

    Returns:
        合議レベル文字列
    """
    if unified_probs and len(unified_probs) >= 2:
        sorted_probs = sorted(unified_probs.values(), reverse=True)
        gap = sorted_probs[0] - sorted_probs[1]
        # 確率差ベースの閾値（スコア差50pt相当≈確率差0.15程度）
        if gap >= 0.15:
            return "明確な上位"
        elif gap >= 0.08:
            return "概ね合意"
        elif gap >= 0.04:
            return "やや接戦"
        else:
            return "混戦"

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
# Phase 7: 統合単勝率・期待値計算
# =============================================================================


def _compute_unified_win_probabilities(ai_result: dict) -> dict[int, float]:
    """全AIソースのスコアを統合して馬ごとの単勝率を算出する.

    各ソース内でスコアを正規化（score_i / Σscores → 確率）し、
    利用可能なソース間で平均を取り、再正規化して合計1.0にする。

    Returns:
        {horse_number: win_probability} （合計 ≈ 1.0）
    """
    sources = ai_result.get("sources", [])
    if not sources:
        return {}

    # 馬番ごとに各ソースの正規化確率を蓄積
    horse_probs: dict[int, list[float]] = {}

    for source in sources:
        predictions = source.get("predictions", [])
        if not predictions:
            continue

        # ソース内の合計スコア
        scores = {}
        for pred in predictions:
            hn = int(pred.get("horse_number", 0))
            score = float(pred.get("score", 0))
            if hn > 0:
                scores[hn] = score

        total_score = sum(scores.values())
        if total_score <= 0:
            continue  # スコアが全て0のソースはスキップ

        # ソース内正規化
        for hn, score in scores.items():
            prob = score / total_score
            if hn not in horse_probs:
                horse_probs[hn] = []
            horse_probs[hn].append(prob)

    if not horse_probs:
        return {}

    # ソース間平均
    avg_probs = {hn: sum(ps) / len(ps) for hn, ps in horse_probs.items()}

    # 最終正規化（合計=1.0を保証）
    total = sum(avg_probs.values())
    if total <= 0:
        return {}

    return {hn: p / total for hn, p in avg_probs.items()}


def _calculate_ev_from_unified_prob(
    odds: float,
    win_probability: float,
) -> dict:
    """統合単勝率とオッズから期待値を計算する.

    Args:
        odds: オッズ
        win_probability: 統合単勝率

    Returns:
        期待値情報（estimated_probability, expected_return, value_rating, probability_source）
    """
    expected_return = round(odds * win_probability, 2)

    if expected_return >= 1.2:
        value_rating = "妙味あり"
    elif expected_return >= 0.9:
        value_rating = "適正"
    elif expected_return >= 0.7:
        value_rating = "やや割高"
    else:
        value_rating = "割高"

    return {
        "estimated_probability": win_probability,
        "expected_return": expected_return,
        "value_rating": value_rating,
        "probability_source": "AI統合予想",
    }


def _calculate_combination_ev(
    horse_numbers: list[int],
    bet_type: str,
    estimated_odds: float,
    unified_probs: dict[int, float],
    total_runners: int,
) -> dict:
    """統合単勝率からHarvilleモデルで組合せ確率を算出し期待値を返す.

    Args:
        horse_numbers: 馬番リスト
        bet_type: 券種
        estimated_odds: 推定オッズ
        unified_probs: 統合単勝率 {horse_number: probability}
        total_runners: 出走頭数

    Returns:
        期待値情報（combination_probability, expected_return, value_rating）
    """
    prob = 0.0

    if bet_type == "win":
        hn = horse_numbers[0]
        prob = unified_probs.get(hn, 0.0)

    elif bet_type == "place":
        hn = horse_numbers[0]
        # 複勝は近似として単勝率の3倍（3着内）
        prob = min(1.0, unified_probs.get(hn, 0.0) * 3)

    elif bet_type == "quinella":
        # 馬連: exacta(A,B) + exacta(B,A)
        p_a = unified_probs.get(horse_numbers[0], 0.0)
        p_b = unified_probs.get(horse_numbers[1], 0.0)
        prob = _harville_exacta(p_a, p_b) + _harville_exacta(p_b, p_a)

    elif bet_type == "exacta":
        # 馬単: exacta(A,B)
        p_a = unified_probs.get(horse_numbers[0], 0.0)
        p_b = unified_probs.get(horse_numbers[1], 0.0)
        prob = _harville_exacta(p_a, p_b)

    elif bet_type == "quinella_place":
        # ワイド: 全非選択馬Cの6順列trifecta合算
        p_a = unified_probs.get(horse_numbers[0], 0.0)
        p_b = unified_probs.get(horse_numbers[1], 0.0)
        selected = set(horse_numbers)
        for hn_c, p_c in unified_probs.items():
            if hn_c in selected:
                continue
            prob += _harville_trifecta(p_a, p_b, p_c)
            prob += _harville_trifecta(p_a, p_c, p_b)
            prob += _harville_trifecta(p_b, p_a, p_c)
            prob += _harville_trifecta(p_b, p_c, p_a)
            prob += _harville_trifecta(p_c, p_a, p_b)
            prob += _harville_trifecta(p_c, p_b, p_a)

    elif bet_type == "trio":
        # 三連複: 6順列trifecta合算
        p_a = unified_probs.get(horse_numbers[0], 0.0)
        p_b = unified_probs.get(horse_numbers[1], 0.0)
        p_c = unified_probs.get(horse_numbers[2], 0.0)
        prob = (
            _harville_trifecta(p_a, p_b, p_c)
            + _harville_trifecta(p_a, p_c, p_b)
            + _harville_trifecta(p_b, p_a, p_c)
            + _harville_trifecta(p_b, p_c, p_a)
            + _harville_trifecta(p_c, p_a, p_b)
            + _harville_trifecta(p_c, p_b, p_a)
        )

    elif bet_type == "trifecta":
        # 三連単: trifecta(A,B,C)
        p_a = unified_probs.get(horse_numbers[0], 0.0)
        p_b = unified_probs.get(horse_numbers[1], 0.0)
        p_c = unified_probs.get(horse_numbers[2], 0.0)
        prob = _harville_trifecta(p_a, p_b, p_c)

    expected_return = round(estimated_odds * prob, 2)

    if expected_return >= 1.2:
        value_rating = "妙味あり"
    elif expected_return >= 0.9:
        value_rating = "適正"
    elif expected_return >= 0.7:
        value_rating = "やや割高"
    else:
        value_rating = "割高"

    return {
        "combination_probability": prob,
        "expected_return": expected_return,
        "value_rating": value_rating,
    }


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
    character_type: str | None = None,
    max_bets: int | None = None,
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
    unified_probs: dict[int, float] | None = None,
    bankroll: int = 0,
    betting_preference: dict | None = None,
) -> dict:
    """買い目提案の統合実装（テスト用に公開）.

    Args:
        race_id: レースID
        budget: 予算（従来モード）
        runners_data: 出走馬データ
        ai_predictions: AI予想データ
        race_name: レース名
        race_conditions: レース条件
        venue: 競馬場名
        total_runners: 出走頭数
        running_styles: 脚質データ
        preferred_bet_types: ユーザー指定の券種リスト
        axis_horses: ユーザー指定の軸馬番号リスト
        character_type: ペルソナ種別（"analyst"/"intuition"/"conservative"/"aggressive"）。
            未指定またはNoneの場合はデフォルト（analyst相当）を使用。
        max_bets: 買い目点数上限。未指定の場合はペルソナのデフォルト値
            （analystは8、conservativeは5など）。指定時はペルソナのデフォルトより優先。
        bankroll: 1日の総資金（bankrollモード）。0より大きい場合はダッチング配分を使用。
        betting_preference: 好み設定辞書（bet_type_preference, target_style, priority）

    Returns:
        統合提案結果
    """
    race_conditions = race_conditions or []
    running_styles = running_styles or []

    # ペルソナ設定 + 好み設定の解決
    config = _get_preference_config(character_type, betting_preference)
    use_bankroll = bankroll > 0
    if use_bankroll:
        effective_max_bets = max_bets  # bankrollモード: max_bets未指定なら全件
    else:
        effective_max_bets = max_bets if max_bets is not None else config["max_bets"]

    # Phase 2: ペース予想
    front_runners = 0
    for rs in running_styles:
        if rs.get("running_style") == "逃げ":
            front_runners += 1
    predicted_pace = _predict_pace(front_runners, total_runners) if running_styles else ""

    # Phase 2: 軸馬選定
    selected_axis = _select_axis_horses(
        runners_data, ai_predictions, predicted_pace, running_styles, axis_horses,
        weight_ai_score=config["weight_ai_score"],
        weight_odds_gap=config["weight_odds_gap"],
        weight_pace_compat=config["weight_pace_compat"],
        speed_index_data=speed_index_data,
        past_performance_data=past_performance_data,
        weight_speed_index=config["weight_speed_index"],
        weight_form=config["weight_form"],
        unified_probs=unified_probs,
    )

    # Phase 3: レース難易度判定 + 券種選定
    difficulty = _assess_race_difficulty(
        total_runners, race_conditions, venue, runners_data
    )
    bet_types = _select_bet_types_by_difficulty(
        difficulty["difficulty_stars"], preferred_bet_types,
        difficulty_bet_types=config["difficulty_bet_types"],
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

    # bankrollモード: confidence_factorでレース予算を算出
    confidence_factor = 0.0
    race_budget = 0
    if use_bankroll:
        confidence_factor = _calculate_confidence_factor(skip["skip_score"])
        raw_budget = bankroll * config["base_rate"] * confidence_factor
        raw_race_budget = int(math.floor(raw_budget / MIN_BET_AMOUNT) * MIN_BET_AMOUNT)
        max_race_budget_cap = int(
            math.floor((bankroll * MAX_RACE_BUDGET_RATIO) / MIN_BET_AMOUNT) * MIN_BET_AMOUNT
        )
        race_budget = min(raw_race_budget, max_race_budget_cap)
        effective_budget = race_budget
    else:
        effective_budget = budget
        if skip["skip_score"] >= config["skip_gate_threshold"]:
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
        max_bets=effective_max_bets,
        torigami_threshold=config["torigami_threshold"],
        weight_ai_score=config["weight_ai_score"],
        weight_odds_gap=config["weight_odds_gap"],
        weight_pace_compat=config["weight_pace_compat"],
        speed_index_data=speed_index_data,
        past_performance_data=past_performance_data,
        weight_speed_index=config["weight_speed_index"],
        weight_form=config["weight_form"],
        unified_probs=unified_probs,
        max_partners=config["max_partners"],
    )

    # Phase 5: 予算配分
    if use_bankroll:
        bets = _allocate_budget_dutching(bets, effective_budget)
    else:
        bets = _allocate_budget(
            bets, effective_budget,
            allocation_high=config["allocation_high"],
            allocation_medium=config["allocation_medium"],
            allocation_low=config["allocation_low"],
        )

    # 合計金額
    total_amount = sum(b.get("amount", 0) for b in bets)

    # AI合議レベル
    ai_consensus = _assess_ai_consensus(ai_predictions, unified_probs=unified_probs)

    # 提案根拠テキスト生成
    proposal_reasoning = _generate_proposal_reasoning(
        axis_horses=selected_axis,
        difficulty=difficulty,
        predicted_pace=predicted_pace,
        ai_consensus=ai_consensus,
        skip=skip,
        bets=bets,
        preferred_bet_types=preferred_bet_types,
        ai_predictions=ai_predictions,
        runners_data=runners_data,
        skip_gate_threshold=config["skip_gate_threshold"],
        max_partners=config["max_partners"],
        speed_index_data=speed_index_data,
        past_performance_data=past_performance_data,
    )

    # 分析コメント生成
    analysis_comment = _generate_analysis_comment(
        selected_axis, difficulty, predicted_pace, skip, ai_consensus, bets,
        skip_gate_threshold=config["skip_gate_threshold"],
    )

    result = {
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
        "proposal_reasoning": proposal_reasoning,
        "analysis_comment": analysis_comment,
        "disclaimer": "データ分析に基づく情報提供です。最終判断はご自身でお願いします。",
    }

    if use_bankroll:
        result["race_budget"] = race_budget
        result["confidence_factor"] = confidence_factor
        result["bankroll_usage_pct"] = round(
            total_amount / bankroll * 100, 2
        ) if bankroll > 0 else 0

    return result


def _generate_proposal_reasoning(
    axis_horses: list[dict],
    difficulty: dict,
    predicted_pace: str,
    ai_consensus: str,
    skip: dict,
    bets: list[dict],
    preferred_bet_types: list[str] | None,
    ai_predictions: list[dict],
    runners_data: list[dict],
    skip_gate_threshold: int = SKIP_GATE_THRESHOLD,
    max_partners: int = MAX_PARTNERS,
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
) -> str:
    """提案根拠テキストを4セクションで生成する.

    Args:
        axis_horses: 軸馬リスト（horse_number, horse_name, composite_score）
        difficulty: 難易度dict（difficulty_stars, difficulty_label）
        predicted_pace: ペース予想文字列
        ai_consensus: AI合議レベル文字列
        skip: 見送り判定dict（skip_score, reasons, recommendation）
        bets: 生成された買い目リスト
        preferred_bet_types: ユーザー指定の券種（None可）
        ai_predictions: AI予想データ
        runners_data: 出走馬データ
        skip_gate_threshold: 見送りゲート閾値

    Returns:
        提案根拠テキスト（4セクション、改行区切り）
    """
    sections = []

    # AI順位マップ（Decimal対策）
    ai_rank_map = {
        int(p.get("horse_number", 0)): int(p.get("rank", 99))
        for p in ai_predictions
    }
    ai_score_map = {
        int(p.get("horse_number", 0)): float(p.get("score", 0))
        for p in ai_predictions
    }

    # 出走馬マップ
    runners_map = {r.get("horse_number"): r for r in runners_data}

    # --- 軸馬選定 ---
    axis_parts = []
    for ax in axis_horses:
        hn = ax["horse_number"]
        name = ax.get("horse_name", "")
        composite_score = float(ax.get("composite_score", 0))
        ai_rank = ai_rank_map.get(hn, 99)
        ai_score = ai_score_map.get(hn, 0)
        runner = runners_map.get(hn, {})
        odds = runner.get("odds", 0)

        desc = (
            f"{hn}番{name}（AI指数{ai_rank}位・{ai_score:.0f}pt、"
            f"総合評価{composite_score:.1f}pt）を軸に選定"
        )
        details = []
        if odds and odds > 0:
            details.append(f"単勝オッズ{float(odds):.1f}倍")
        if ai_rank <= 3:
            details.append("AI指数が上位で信頼度が高い")
        if predicted_pace:
            # ペース予想に基づく一般的な脚質傾向の説明
            if predicted_pace == "ハイ":
                details.append("ハイペース予想で差し・追込脚質に有利")
            elif predicted_pace == "スロー":
                details.append("スローペース予想で先行・逃げ脚質に有利")
            else:
                details.append(f"{predicted_pace}ペース予想で幅広い脚質に対応")
        if speed_index_data:
            si_score = _calculate_speed_index_score(hn, speed_index_data)
            if si_score is not None:
                details.append(f"スピード指数評価{si_score:.0f}pt")
        if past_performance_data:
            form_s = _calculate_form_score(hn, past_performance_data)
            if form_s is not None:
                details.append(f"近走フォーム{form_s:.0f}pt")

        if details:
            desc += "。" + "、".join(details)
        axis_parts.append(desc)

    sections.append("【軸馬選定】" + "。".join(axis_parts))

    # --- 券種選定 ---
    stars = difficulty.get("difficulty_stars", 3)
    label = difficulty.get("difficulty_label", "")
    bet_type_names_in_bets = list(dict.fromkeys(b.get("bet_type_name", "") for b in bets))

    if preferred_bet_types:
        pref_names = [BET_TYPE_NAMES.get(bt, bt) for bt in preferred_bet_types]
        ticket_desc = f"ユーザー指定により{'・'.join(pref_names)}を選定"
    else:
        ticket_desc = (
            f"レース難易度{'★' * stars}（{label}）のため"
            f"{'・'.join(bet_type_names_in_bets)}を自動選定"
        )

    # 上位馬のスコア差に基づく補足
    sorted_preds = sorted(ai_predictions, key=lambda x: float(x.get("score", 0)), reverse=True)
    if len(sorted_preds) >= 2:
        top_score = float(sorted_preds[0].get("score", 0))
        second_score = float(sorted_preds[1].get("score", 0))
        gap = top_score - second_score
        if gap >= 20:
            ticket_desc += "。上位馬のAI指数差が大きく、軸からの流しが有効と判断"
        elif gap < 10:
            ticket_desc += "。AI指数が接戦のため手広く構える券種が有効と判断"

    sections.append("【券種】" + ticket_desc)

    # --- 組み合わせ ---
    axis_numbers = {ax["horse_number"] for ax in axis_horses}
    # betsから相手馬を抽出（軸馬以外）
    partner_numbers_seen = []
    for bet in bets:
        for hn in bet.get("horse_numbers", []):
            if hn not in axis_numbers and hn not in partner_numbers_seen:
                partner_numbers_seen.append(hn)

    partner_descs = []
    for hn in partner_numbers_seen[:max_partners]:
        runner = runners_map.get(hn, {})
        name = runner.get("horse_name", "")
        ai_rank = ai_rank_map.get(hn, 99)
        # 期待値は買い目から取得（その馬を含む買い目の最大期待値）
        ev_vals = [
            b.get("expected_value", 0) for b in bets
            if hn in b.get("horse_numbers", [])
        ]
        max_ev = max(ev_vals) if ev_vals else 0
        desc = f"{hn}番{name}（AI{ai_rank}位"
        if max_ev > 0:
            desc += f"・期待値{max_ev}"
        desc += "）"
        partner_descs.append(desc)

    if partner_descs:
        combo_text = f"相手は{'、'.join(partner_descs)}を選定"
        combo_text += "。いずれもAI上位集団に属し、オッズとの乖離から妙味あり"
    else:
        combo_text = "単勝・複勝の軸馬単独買い"

    sections.append("【組み合わせ】" + combo_text)

    # --- リスク ---
    risk_parts = []
    risk_parts.append(f"AI合議「{ai_consensus}」")
    if ai_consensus in ("明確な上位", "概ね合意"):
        risk_parts.append("上位馬の信頼度は高い")
    elif ai_consensus == "混戦":
        risk_parts.append("上位馬の力差が小さく波乱含み")

    skip_score = skip.get("skip_score", 0)
    risk_parts.append(f"見送りスコア{skip_score}/10")
    if skip_score >= skip_gate_threshold:
        risk_parts.append("高リスクのため予算50%削減で提案")
    elif skip_score >= 5:
        risk_parts.append("慎重な検討を推奨")
    else:
        risk_parts.append("積極参戦レベル")

    # トリガミリスクの確認（Decimal対策でfloat変換、閾値は定数を使用）
    has_torigami_risk = any(
        float(b.get("composite_odds", 0)) > 0
        and float(b.get("composite_odds", 0)) < float(TORIGAMI_COMPOSITE_ODDS_THRESHOLD)
        for b in bets
    )
    if has_torigami_risk:
        risk_parts.append("一部低オッズの買い目あり、トリガミに注意")
    else:
        risk_parts.append("トリガミリスクなし")

    sections.append("【リスク】" + "。".join(risk_parts))

    return "\n\n".join(sections)


def _generate_analysis_comment(
    axis_horses: list[dict],
    difficulty: dict,
    predicted_pace: str,
    skip: dict,
    ai_consensus: str,
    bets: list[dict],
    skip_gate_threshold: int = SKIP_GATE_THRESHOLD,
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
    if skip["skip_score"] >= skip_gate_threshold:
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
    budget: int = 0,
    bankroll: int = 0,
    preferred_bet_types: list[str] | None = None,
    axis_horses: list[int] | None = None,
    character_type: str | None = None,
    max_bets: int | None = None,
) -> dict:
    """レース分析に基づき、買い目の提案を一括生成する.

    AI指数・レース難易度・展開予想を統合し、
    軸馬選定 → 券種選定 → 買い目生成 → 予算配分を自動で行う。

    bankroll指定時はダッチング方式（均等払い戻し配分）で配分する。
    budget指定時は従来の信頼度別配分を使用する。

    Args:
        race_id: レースID (例: "20260201_05_11")
        budget: 予算（円）。従来モード。
        bankroll: 1日の総資金（円）。ダッチング配分モード。
        preferred_bet_types: 券種の指定リスト (省略時はレース難易度から自動選定)
            "win", "place", "quinella", "quinella_place", "exacta", "trio", "trifecta"
        axis_horses: 軸馬の馬番リスト (省略時はAI指数上位から自動選定)
        character_type: ペルソナ種別 ("analyst", "intuition", "conservative", "aggressive")
        max_bets: 買い目点数上限 (省略時はペルソナのデフォルト値)

    Returns:
        提案結果:
        - race_summary: レース概要（難易度、ペース、AI合議、見送りスコア）
        - proposed_bets: 提案買い目リスト（券種、馬番、金額、期待値、合成オッズ）
        - total_amount: 合計金額
        - budget_remaining: 残り予算
        - analysis_comment: 分析ナラティブ
        - disclaimer: 免責事項
        (bankrollモード時は追加: race_budget, confidence_factor, bankroll_usage_pct)
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
        unified_probs = {}
        if isinstance(ai_result, dict):
            sources = ai_result.get("sources", [])
            if sources:
                ai_predictions = sources[0].get("predictions", [])
                unified_probs = _compute_unified_win_probabilities(ai_result)
            elif ai_result.get("predictions"):
                ai_predictions = ai_result["predictions"]

        # 脚質データ取得
        running_styles = _get_running_styles(race_id)

        # スピード指数データ取得
        from .speed_index import get_speed_index
        speed_index_data = None
        si_result = get_speed_index(race_id)
        if isinstance(si_result, dict) and "error" not in si_result:
            speed_index_data = si_result

        # 過去成績データ取得
        from .past_performance import get_past_performance
        past_performance_data = None
        pp_result = get_past_performance(race_id)
        if isinstance(pp_result, dict) and "error" not in pp_result:
            past_performance_data = pp_result

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
            character_type=character_type,
            max_bets=max_bets,
            speed_index_data=speed_index_data,
            past_performance_data=past_performance_data,
            unified_probs=unified_probs or None,
            bankroll=bankroll,
            betting_preference=_current_betting_preference,
        )
        if "error" not in result:
            _last_proposal_result = result
        return result
    except requests.RequestException as e:
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        return {"error": f"提案生成に失敗しました: {str(e)}"}
