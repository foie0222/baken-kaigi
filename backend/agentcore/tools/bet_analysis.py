"""買い目分析ツール.

選択された買い目を分析し、データに基づくフィードバックを生成する。
JRA統計に基づく券種別確率、出走頭数補正、レース条件補正を適用。
合成オッズ計算、AI指数内訳分析、資金配分最適化を含む。
"""

import math

from strands import tool

from .common import log_tool_execution

# 券種の日本語表示名
BET_TYPE_NAMES = {
    "win": "単勝",
    "place": "複勝",
    "quinella": "馬連",
    "quinella_place": "ワイド",
    "exacta": "馬単",
    "trio": "三連複",
    "trifecta": "三連単",
}

# =============================================================================
# JRA過去統計に基づく人気別確率テーブル（18頭立て基準）
# 出典: JRA公式統計データ（概算値）
# =============================================================================

# 単勝: 1着率
WIN_RATE_BY_POPULARITY = {
    1: 0.33, 2: 0.19, 3: 0.13, 4: 0.09, 5: 0.07,
    6: 0.05, 7: 0.04, 8: 0.03, 9: 0.02, 10: 0.02,
    11: 0.01, 12: 0.01, 13: 0.005, 14: 0.005,
    15: 0.003, 16: 0.003, 17: 0.002, 18: 0.002,
}

# 複勝/ワイド: 3着内率
PLACE_RATE_BY_POPULARITY = {
    1: 0.65, 2: 0.52, 3: 0.43, 4: 0.35, 5: 0.30,
    6: 0.25, 7: 0.20, 8: 0.16, 9: 0.13, 10: 0.10,
    11: 0.08, 12: 0.06, 13: 0.05, 14: 0.04,
    15: 0.03, 16: 0.025, 17: 0.02, 18: 0.015,
}

# 馬連/馬単: 2着内率
EXACTA_RATE_BY_POPULARITY = {
    1: 0.52, 2: 0.38, 3: 0.30, 4: 0.24, 5: 0.19,
    6: 0.15, 7: 0.12, 8: 0.10, 9: 0.08, 10: 0.06,
    11: 0.05, 12: 0.04, 13: 0.03, 14: 0.025,
    15: 0.02, 16: 0.015, 17: 0.01, 18: 0.01,
}

# =============================================================================
# 出走頭数による補正係数
# 頭数が少ないほど上位人気の勝率は上がる
# =============================================================================

RUNNERS_CORRECTION = {
    # (頭数, 人気) -> 補正係数
    # 8頭立ての1番人気は18頭立てより勝ちやすい
    8: {1: 1.25, 2: 1.20, 3: 1.15, 4: 1.10, 5: 1.05, 6: 1.0, 7: 0.95, 8: 0.90},
    10: {1: 1.15, 2: 1.12, 3: 1.10, 4: 1.08, 5: 1.05, 6: 1.0, 7: 0.97, 8: 0.95, 9: 0.93, 10: 0.90},
    12: {1: 1.10, 2: 1.08, 3: 1.06, 4: 1.04, 5: 1.02},
    14: {1: 1.05, 2: 1.04, 3: 1.03, 4: 1.02, 5: 1.01},
    16: {1: 1.02, 2: 1.01, 3: 1.01},
    18: {},  # 基準値（補正なし）
}

# =============================================================================
# 複勝オッズ推定: 単勝に対する複勝オッズの比率（人気別）
# 出典: JRA統計に基づく概算値
# =============================================================================

WIN_TO_PLACE_RATIO = {
    1: 0.73, 2: 0.55, 3: 0.45, 4: 0.38, 5: 0.33,
    6: 0.28, 7: 0.24, 8: 0.21, 9: 0.19, 10: 0.17,
}

# =============================================================================
# レース条件による補正係数
# 荒れやすいレースでは人気馬の信頼度が下がる
# =============================================================================

RACE_CONDITION_CORRECTION = {
    # 通常レース（補正なし）
    "normal": 1.0,
    # ハンデ戦: 人気馬の勝率が下がる傾向
    "handicap": 0.85,
    # 牝馬限定戦: やや荒れやすい
    "fillies_mares": 0.92,
    # 新馬戦: データ不足で荒れやすい
    "maiden_new": 0.88,
    # 未勝利戦: やや荒れやすい
    "maiden": 0.93,
    # G1: 実力馬が揃い堅い傾向
    "g1": 1.05,
    # 障害戦: 荒れやすい
    "hurdle": 0.80,
    # ダート替わり/芝替わり: 不確定要素
    "surface_change": 0.90,
}


def _harville_exacta(p_a: float, p_b: float) -> float:
    """Harvilleモデルによる馬単確率: P(A=1着, B=2着).

    Args:
        p_a: Aの勝率
        p_b: Bの勝率

    Returns:
        A1着B2着の確率
    """
    if p_a >= 1.0 or p_a <= 0.0:
        return 0.0
    return p_a * p_b / (1 - p_a)


def _harville_trifecta(p_a: float, p_b: float, p_c: float) -> float:
    """Harvilleモデルによる三連単確率: P(A=1着, B=2着, C=3着).

    Args:
        p_a: Aの勝率
        p_b: Bの勝率
        p_c: Cの勝率

    Returns:
        A1着B2着C3着の確率
    """
    if p_a >= 1.0 or (p_a + p_b) >= 1.0:
        return 0.0
    if p_a <= 0.0:
        return 0.0
    return p_a * (p_b / (1 - p_a)) * (p_c / (1 - p_a - p_b))


def _estimate_win_probability(
    popularity: int,
    total_runners: int = 18,
    race_conditions: list[str] | None = None,
) -> float:
    """Harvilleモデル用の正規化済み勝率を返す.

    Harvilleモデルは「全馬の勝率の合計=1」を前提とするため、
    _estimate_probability で頭数補正等を行った後の値を
    全人気(1..total_runners)について正規化する。

    Args:
        popularity: 人気順位
        total_runners: 出走頭数
        race_conditions: レース条件

    Returns:
        推定勝率（全馬で合計1となるよう正規化済み）
    """
    raw_probs = [
        _estimate_probability(pop, "win", total_runners, race_conditions)
        for pop in range(1, total_runners + 1)
    ]

    total_prob = sum(raw_probs)
    if total_prob <= 0.0:
        return 0.0

    index = popularity - 1
    if index < 0 or index >= len(raw_probs):
        return 0.0

    return raw_probs[index] / total_prob


def _harville_wide(
    p_a: float,
    p_b: float,
    total_runners: int,
    selected_pops: list[int],
    race_conditions: list[str] | None,
) -> float:
    """Harvilleモデルによるワイド確率: P(A,Bが共に3着内).

    全非選択馬Cについて、(A,B,C)の6順列のtrifecta確率を合算する。

    Args:
        p_a: Aの勝率
        p_b: Bの勝率
        total_runners: 出走頭数
        selected_pops: 選択馬の人気順位リスト
        race_conditions: レース条件

    Returns:
        両馬が3着内に入る確率
    """
    total = 0.0
    for pop_c in range(1, total_runners + 1):
        if pop_c in selected_pops:
            continue
        p_c = _estimate_win_probability(pop_c, total_runners, race_conditions)
        # 6順列: (A,B,C), (A,C,B), (B,A,C), (B,C,A), (C,A,B), (C,B,A)
        total += _harville_trifecta(p_a, p_b, p_c)
        total += _harville_trifecta(p_a, p_c, p_b)
        total += _harville_trifecta(p_b, p_a, p_c)
        total += _harville_trifecta(p_b, p_c, p_a)
        total += _harville_trifecta(p_c, p_a, p_b)
        total += _harville_trifecta(p_c, p_b, p_a)
    return total


def _estimate_place_odds_ratio(popularity: int) -> float:
    """人気別の複勝オッズ比率を返す.

    単勝オッズに対する複勝オッズの比率。

    Args:
        popularity: 人気順位

    Returns:
        複勝オッズ比率
    """
    return WIN_TO_PLACE_RATIO.get(popularity, 0.16)


def _get_runners_correction(total_runners: int, popularity: int) -> float:
    """出走頭数による補正係数を取得する（線形補間版）.

    Args:
        total_runners: 出走頭数
        popularity: 人気順位

    Returns:
        補正係数（1.0が基準）
    """
    available_runners = sorted(RUNNERS_CORRECTION.keys())

    # 範囲外: 最小テーブル値 or 最大テーブル値を使用
    if total_runners <= available_runners[0]:
        return RUNNERS_CORRECTION[available_runners[0]].get(popularity, 1.0)
    if total_runners >= available_runners[-1]:
        return RUNNERS_CORRECTION[available_runners[-1]].get(popularity, 1.0)

    # テーブルに完全一致する場合
    if total_runners in RUNNERS_CORRECTION:
        return RUNNERS_CORRECTION[total_runners].get(popularity, 1.0)

    # 隣接2テーブル間で線形補間
    lower = max(r for r in available_runners if r < total_runners)
    upper = min(r for r in available_runners if r > total_runners)

    lower_corr = RUNNERS_CORRECTION[lower].get(popularity, 1.0)
    upper_corr = RUNNERS_CORRECTION[upper].get(popularity, 1.0)

    t = (total_runners - lower) / (upper - lower)
    return lower_corr + t * (upper_corr - lower_corr)


def _get_race_condition_correction(race_conditions: list[str] | None) -> float:
    """レース条件による補正係数を取得する.

    Args:
        race_conditions: レース条件のリスト

    Returns:
        補正係数（荒れやすい条件があれば最小値、なければ最大値を適用）
    """
    if not race_conditions:
        return 1.0

    corrections = [
        RACE_CONDITION_CORRECTION.get(condition, 1.0)
        for condition in race_conditions
    ]

    if not corrections:
        return 1.0

    # 荒れやすい条件（<1.0）があれば、最小値を適用（荒れを優先）
    # なければ、最大値を適用（G1などの堅い傾向）
    negative_corrections = [c for c in corrections if c < 1.0]
    if negative_corrections:
        return min(negative_corrections)
    else:
        return max(corrections)


def _estimate_probability(
    popularity: int,
    bet_type: str,
    total_runners: int = 18,
    race_conditions: list[str] | None = None,
) -> float:
    """券種・頭数・レース条件を考慮した確率を推定する.

    Args:
        popularity: 人気順位
        bet_type: 券種
        total_runners: 出走頭数
        race_conditions: レース条件リスト

    Returns:
        推定確率（0.0-1.0）
    """
    if popularity <= 0:
        return 0.01

    # 券種に応じたベース確率を取得
    if bet_type == "win":
        base_prob = WIN_RATE_BY_POPULARITY.get(popularity, 0.002)
    elif bet_type in ("place", "quinella_place"):
        base_prob = PLACE_RATE_BY_POPULARITY.get(popularity, 0.015)
    elif bet_type in ("quinella", "exacta"):
        base_prob = EXACTA_RATE_BY_POPULARITY.get(popularity, 0.01)
    elif bet_type in ("trio", "trifecta"):
        # 三連系は3着内率を使用
        base_prob = PLACE_RATE_BY_POPULARITY.get(popularity, 0.015)
    else:
        base_prob = WIN_RATE_BY_POPULARITY.get(popularity, 0.002)

    # 出走頭数補正
    runners_correction = _get_runners_correction(total_runners, popularity)

    # レース条件補正
    condition_correction = _get_race_condition_correction(race_conditions)

    # 補正後の確率（上限1.0）
    adjusted_prob = min(base_prob * runners_correction * condition_correction, 0.99)

    return adjusted_prob


def _calculate_expected_value(
    odds: float,
    popularity: int,
    bet_type: str = "win",
    total_runners: int = 18,
    race_conditions: list[str] | None = None,
) -> dict:
    """期待値を計算する.

    Args:
        odds: オッズ
        popularity: 人気順位
        bet_type: 券種
        total_runners: 出走頭数
        race_conditions: レース条件

    Returns:
        期待値分析結果
    """
    odds = float(odds)
    popularity = int(popularity)
    if odds <= 0:
        return {
            "estimated_probability": 0,
            "expected_return": 0,
            "value_rating": "データ不足",
            "probability_source": "N/A",
        }

    estimated_prob = _estimate_probability(
        popularity, bet_type, total_runners, race_conditions
    )
    expected_return = odds * estimated_prob

    # 期待値の評価
    if expected_return >= 1.2:
        rating = "妙味あり"
    elif expected_return >= 0.9:
        rating = "適正"
    elif expected_return >= 0.7:
        rating = "やや割高"
    else:
        rating = "割高"

    # 確率の根拠を説明
    if bet_type == "win":
        prob_source = f"JRA統計: {popularity}番人気の勝率"
    elif bet_type in ("place", "quinella_place"):
        prob_source = f"JRA統計: {popularity}番人気の3着内率"
    elif bet_type in ("quinella", "exacta"):
        prob_source = f"JRA統計: {popularity}番人気の2着内率"
    else:
        prob_source = f"JRA統計: {popularity}番人気の3着内率"

    return {
        "estimated_probability": round(estimated_prob * 100, 1),
        "expected_return": round(expected_return, 2),
        "value_rating": rating,
        "probability_source": prob_source,
    }


def _calculate_combination_probability(
    popularities: list[int],
    bet_type: str,
    total_runners: int = 18,
    race_conditions: list[str] | None = None,
) -> dict:
    """組み合わせ馬券の的中確率を推定する.

    Args:
        popularities: 選択馬の人気順位リスト
        bet_type: 券種
        total_runners: 出走頭数
        race_conditions: レース条件

    Returns:
        組み合わせ確率分析結果
    """
    if not popularities:
        return {"probability": 0, "method": "N/A"}

    # 各馬のWIN確率を取得（Harvilleモデルの入力）
    def _win_prob(pop: int) -> float:
        return _estimate_win_probability(pop, total_runners, race_conditions)

    if bet_type == "quinella":
        # 馬連: Harville(A→B) + Harville(B→A)
        if len(popularities) < 2:
            return {"probability": 0, "method": "馬番不足"}

        w1, w2 = _win_prob(popularities[0]), _win_prob(popularities[1])
        combined_prob = _harville_exacta(w1, w2) + _harville_exacta(w2, w1)
        method = "Harvilleモデル（馬連: 2順列合算）"

    elif bet_type == "quinella_place":
        # ワイド: Harvilleワイドモデル（3着内に両馬が入る全順列）
        if len(popularities) < 2:
            return {"probability": 0, "method": "馬番不足"}

        w1, w2 = _win_prob(popularities[0]), _win_prob(popularities[1])
        combined_prob = _harville_wide(
            w1, w2, total_runners, popularities[:2], race_conditions
        )
        method = "Harvilleモデル（ワイド: 全3着内順列合算）"

    elif bet_type == "exacta":
        # 馬単: Harville(1着→2着)
        if len(popularities) < 2:
            return {"probability": 0, "method": "馬番不足"}

        w1, w2 = _win_prob(popularities[0]), _win_prob(popularities[1])
        combined_prob = _harville_exacta(w1, w2)
        method = "Harvilleモデル（馬単）"

    elif bet_type == "trio":
        # 三連複: 6順列のtrifecta合算
        if len(popularities) < 3:
            return {"probability": 0, "method": "馬番不足"}

        w1 = _win_prob(popularities[0])
        w2 = _win_prob(popularities[1])
        w3 = _win_prob(popularities[2])
        combined_prob = (
            _harville_trifecta(w1, w2, w3) + _harville_trifecta(w1, w3, w2)
            + _harville_trifecta(w2, w1, w3) + _harville_trifecta(w2, w3, w1)
            + _harville_trifecta(w3, w1, w2) + _harville_trifecta(w3, w2, w1)
        )
        method = "Harvilleモデル（三連複: 6順列合算）"

    elif bet_type == "trifecta":
        # 三連単: Harville(1着→2着→3着)
        if len(popularities) < 3:
            return {"probability": 0, "method": "馬番不足"}

        w1 = _win_prob(popularities[0])
        w2 = _win_prob(popularities[1])
        w3 = _win_prob(popularities[2])
        combined_prob = _harville_trifecta(w1, w2, w3)
        method = "Harvilleモデル（三連単）"

    else:
        # 単勝・複勝は組み合わせ不要
        return {"probability": 0, "method": "単独券種"}

    # 丸め誤差や正規化不足で1.0を超えないようクランプ
    combined_prob = max(0.0, min(combined_prob, 1.0))

    return {
        "probability": round(combined_prob * 100, 2),
        "method": method,
    }


def _analyze_weaknesses(
    selected_horses: list[dict],
    bet_type: str,
    total_runners: int,
    race_conditions: list[str] | None = None,
) -> list[str]:
    """買い目の弱点を分析する.

    Args:
        selected_horses: 選択された馬のリスト
        bet_type: 券種
        total_runners: 出走頭数
        race_conditions: レース条件

    Returns:
        弱点リスト
    """
    weaknesses = []

    if not selected_horses:
        return weaknesses

    popularities = [h.get("popularity") or 99 for h in selected_horses]

    # 1. 人気馬偏重チェック
    popular_count = sum(1 for p in popularities if p <= 3)
    if popular_count == len(selected_horses) and len(selected_horses) >= 2:
        weaknesses.append(
            f"人気馬のみの選択（{popular_count}頭中{popular_count}頭が3番人気以内）。"
            "1頭でも飛ぶと全滅リスク"
        )

    # 2. 穴馬偏重チェック
    longshot_count = sum(1 for p in popularities if p >= 10)
    if longshot_count == len(selected_horses) and len(selected_horses) >= 2:
        weaknesses.append(
            f"穴馬のみの選択（全{len(selected_horses)}頭が10番人気以下）。"
            "的中率が極めて低い"
        )

    # 3. 最下位人気の警告
    for h in selected_horses:
        pop = h.get("popularity") or 0
        if pop >= total_runners and total_runners > 0:
            prob = _estimate_probability(pop, bet_type, total_runners, race_conditions)
            weaknesses.append(
                f"{h.get('horse_number')}番 {h.get('horse_name')}は最下位人気。"
                f"統計的入着率は約{prob*100:.1f}%"
            )

    # 4. 1番人気依存チェック
    has_favorite = any(p == 1 for p in popularities)
    if has_favorite and bet_type in ("trio", "trifecta", "quinella", "exacta"):
        # 頭数補正後の勝率を表示
        win_rate = _estimate_probability(1, "win", total_runners, race_conditions)
        weaknesses.append(
            f"1番人気を軸にした買い目。"
            f"JRA統計では勝率約{win_rate*100:.0f}%、つまり{(1-win_rate)*100:.0f}%は外れる"
        )

    # 5. 三連系のトリガミリスク
    if bet_type in ("trio", "trifecta") and len(selected_horses) >= 3:
        avg_pop = sum(popularities) / len(popularities)
        if avg_pop <= 3:
            weaknesses.append(
                "三連系で人気馬中心の組み合わせ。"
                "的中してもトリガミ（配当が投資額以下）の可能性大"
            )

    # 6. レース条件による警告
    if race_conditions:
        if "handicap" in race_conditions:
            weaknesses.append(
                "ハンデ戦は人気馬の信頼度が低い。荒れる傾向あり"
            )
        if "maiden_new" in race_conditions:
            weaknesses.append(
                "新馬戦はデータ不足で予測困難。荒れやすい"
            )
        if "hurdle" in race_conditions:
            weaknesses.append(
                "障害戦は落馬リスクがあり荒れやすい"
            )

    # 7. 少頭数での高オッズ警告
    if total_runners <= 10:
        high_odds_horses = [
            h for h in selected_horses if (h.get("odds") or 0) >= 20
        ]
        if high_odds_horses:
            weaknesses.append(
                f"少頭数（{total_runners}頭）で高オッズ馬を選択。"
                "少頭数では穴馬が来にくい傾向"
            )

    return weaknesses


def _calculate_torigami_risk(
    bet_type: str,
    selected_horses: list[dict],
    amount: int,
) -> dict:
    """トリガミリスクを計算する.

    Args:
        bet_type: 券種
        selected_horses: 選択された馬のリスト
        amount: 掛け金

    Returns:
        トリガミリスク分析結果
    """
    if not selected_horses or amount <= 0:
        return {
            "risk_level": "不明",
            "estimated_min_return": 0,
            "is_torigami_likely": False,
            "reason": None,
        }

    # 単勝・複勝の場合は最低オッズで計算
    if bet_type in ("win", "place"):
        min_odds = min(h.get("odds") or 999 for h in selected_horses)
        estimated_return = int(min_odds * 100)  # 100円あたりの配当

        if bet_type == "place":
            # 複勝オッズは人気別比率テーブルで推定
            popularity = min(
                (h.get("popularity") or 99 for h in selected_horses), default=99
            )
            ratio = _estimate_place_odds_ratio(popularity)
            estimated_return = int(estimated_return * ratio)

        is_torigami = estimated_return < amount
        risk_level = "高" if is_torigami else "低"

        return {
            "risk_level": risk_level,
            "estimated_min_return": estimated_return,
            "is_torigami_likely": is_torigami,
            "reason": "低オッズ" if is_torigami else None,
        }

    # 三連系の場合は人気馬の組み合わせで判断
    if bet_type in ("trio", "trifecta"):
        popularities = [h.get("popularity") or 99 for h in selected_horses]
        avg_pop = sum(popularities) / len(popularities) if popularities else 99

        # 人気馬ばかりならトリガミリスク高
        if avg_pop <= 3:
            return {
                "risk_level": "高",
                "estimated_min_return": None,
                "is_torigami_likely": True,
                "reason": "人気馬のみの組み合わせ",
            }
        elif avg_pop <= 5:
            return {
                "risk_level": "中",
                "estimated_min_return": None,
                "is_torigami_likely": False,
                "reason": "中人気中心の組み合わせ",
            }

    return {
        "risk_level": "低",
        "estimated_min_return": None,
        "is_torigami_likely": False,
        "reason": None,
    }


def _calculate_composite_odds(odds_list: list[float]) -> dict:
    """合成オッズを計算する.

    合成オッズ = 1 ÷ Σ(1/各オッズ)
    複数の買い目を購入した場合の実質的な倍率を示す。
    合成オッズが2.0未満の場合、トリガミリスクが高い。

    Args:
        odds_list: 各買い目のオッズリスト

    Returns:
        合成オッズ分析結果
    """
    if not odds_list:
        return {
            "composite_odds": 0,
            "is_torigami": False,
            "torigami_warning": None,
            "bet_count": 0,
        }

    valid_odds = [o for o in odds_list if o > 0]
    if not valid_odds:
        return {
            "composite_odds": 0,
            "is_torigami": False,
            "torigami_warning": None,
            "bet_count": 0,
        }

    reciprocal_sum = sum(1.0 / o for o in valid_odds)
    composite_odds = 1.0 / reciprocal_sum if reciprocal_sum > 0 else 0

    is_torigami = composite_odds < 2.0
    if composite_odds < 1.5:
        warning = f"合成オッズ{composite_odds:.1f}倍。高確率でトリガミ。買い目の絞り込みが必要"
    elif composite_odds < 2.0:
        warning = f"合成オッズ{composite_odds:.1f}倍。トリガミリスクあり。資金配分の見直しを推奨"
    elif composite_odds < 3.0:
        warning = f"合成オッズ{composite_odds:.1f}倍。利益は薄いが回収は可能"
    else:
        warning = None

    return {
        "composite_odds": round(composite_odds, 2),
        "is_torigami": is_torigami,
        "torigami_warning": warning,
        "bet_count": len(valid_odds),
    }


def _analyze_ai_index_context(
    ai_predictions: list[dict] | None,
    horse_numbers: list[int],
) -> list[dict]:
    """AI指数の内訳コンテキストを提供する.

    ai-shisu.comのスコアは不透明だが、スコア差や順位間ギャップから
    ユーザーが判断材料にできる情報を抽出する。

    Args:
        ai_predictions: AI予想データリスト
        horse_numbers: 分析対象馬番リスト

    Returns:
        各馬のAI指数コンテキスト分析結果
    """
    if not ai_predictions:
        return []

    # スコア順にソートして全体の分布を把握
    sorted_preds = sorted(ai_predictions, key=lambda x: x.get("score", 0), reverse=True)
    if not sorted_preds:
        return []

    top_score = sorted_preds[0].get("score", 0)
    scores = [p.get("score", 0) for p in sorted_preds]
    results = []
    for pred in sorted_preds:
        horse_num = pred.get("horse_number")
        if horse_num not in horse_numbers:
            continue

        score = pred.get("score", 0)
        rank = pred.get("rank", 99)
        horse_name = pred.get("horse_name", "")

        # スコアの相対的な位置
        score_diff_from_top = top_score - score
        score_ratio = score / top_score if top_score > 0 else 0

        # 上位馬とのギャップ分析
        if rank == 1:
            gap_comment = "AI最上位評価"
            if len(sorted_preds) > 1:
                second_score = sorted_preds[1].get("score", 0)
                gap = score - second_score
                if gap >= 50:
                    gap_comment += f"。2位と{gap}pt差で抜けた評価"
                elif gap >= 20:
                    gap_comment += f"。2位と{gap}pt差で優位"
                else:
                    gap_comment += f"。2位と{gap}pt差で僅差"
        elif rank <= 3:
            prev_score = sorted_preds[rank - 2].get("score", 0) if rank >= 2 else top_score
            gap_to_prev = prev_score - score
            gap_comment = f"AI{rank}位（1位と{score_diff_from_top:.0f}pt差）"
            if gap_to_prev <= 10:
                gap_comment += "。上位と僅差で逆転可能圏"
        elif rank <= 6:
            gap_comment = f"AI{rank}位（1位と{score_diff_from_top:.0f}pt差）。中位評価"
        else:
            gap_comment = f"AI{rank}位（1位と{score_diff_from_top:.0f}pt差）。低評価"

        # スコア水準の解釈
        if score >= 350:
            level = "非常に高い"
        elif score >= 250:
            level = "高い"
        elif score >= 150:
            level = "中程度"
        elif score >= 80:
            level = "低い"
        else:
            level = "非常に低い"

        # 集団分析：この馬が属するクラスターを特定
        cluster = _identify_score_cluster(scores, score)

        results.append({
            "horse_number": horse_num,
            "horse_name": horse_name,
            "ai_rank": rank,
            "ai_score": score,
            "score_level": level,
            "score_ratio_to_top": round(score_ratio, 2),
            "gap_analysis": gap_comment,
            "cluster": cluster,
        })

    return results


def _identify_score_cluster(all_scores: list[float], target_score: float) -> str:
    """スコア分布からクラスター（集団）を特定する.

    Args:
        all_scores: 全馬のスコアリスト（ソート不要、関数内でソート）
        target_score: 対象馬のスコア

    Returns:
        クラスター名
    """
    if not all_scores:
        return "不明"

    sorted_scores = sorted(all_scores, reverse=True)
    n = len(sorted_scores)

    if n <= 3:
        return "少頭数のため集団分析なし"

    # ギャップ検出でグループ分け
    groups: list[list[float]] = [[sorted_scores[0]]]
    for i in range(1, n):
        gap = sorted_scores[i - 1] - sorted_scores[i]
        threshold = max(20, (sorted_scores[0] - sorted_scores[-1]) * 0.15)
        if gap >= threshold:
            groups.append([sorted_scores[i]])
        else:
            groups[-1].append(sorted_scores[i])

    # 対象馬がどのグループに属するか
    for idx, group in enumerate(groups):
        if target_score >= min(group) and target_score <= max(group):
            if idx == 0:
                return f"上位集団（{len(group)}頭）"
            elif idx == len(groups) - 1:
                return f"下位集団（{len(group)}頭）"
            else:
                return f"中位集団（{len(group)}頭）"

    return "単独"


def _optimize_fund_allocation(
    selected_horses: list[dict],
    total_budget: int,
    bet_type: str,
    total_runners: int = 18,
    race_conditions: list[str] | None = None,
) -> dict:
    """資金配分を最適化する.

    ケリー基準の簡易版を用いて、期待値の高い買い目により多く配分する。

    Args:
        selected_horses: 選択された馬のリスト
        total_budget: 総予算
        bet_type: 券種
        total_runners: 出走頭数
        race_conditions: レース条件

    Returns:
        資金配分の提案
    """
    if not selected_horses or total_budget <= 0:
        return {"allocations": [], "strategy": "データ不足"}

    # 単勝・複勝で複数買いの場合のみ資金配分が有効
    if bet_type not in ("win", "place") or len(selected_horses) < 2:
        return {
            "allocations": [],
            "strategy": "単勝・複勝以外の券種、または買い目が1点のため資金配分不要",
        }

    allocations = []
    total_kelly = 0

    for h in selected_horses:
        odds = h.get("odds") or 0
        pop = h.get("popularity") or 99

        if odds <= 0:
            continue

        prob = _estimate_probability(pop, bet_type, total_runners, race_conditions)
        expected_return = odds * prob

        # 簡易ケリー基準: f = (p*b - q) / b
        # p = 勝率、b = オッズ-1（純利益倍率）、q = 1-p
        b = odds - 1
        if b <= 0:
            kelly_fraction = 0
        else:
            kelly_fraction = max(0, (prob * b - (1 - prob)) / b)

        # 保守的にケリー比率の1/4を使用（フラクショナルケリー）
        kelly_fraction *= 0.25

        allocations.append({
            "horse_number": h.get("horse_number"),
            "horse_name": h.get("horse_name"),
            "odds": odds,
            "estimated_probability": round(prob * 100, 1),
            "expected_return": round(expected_return, 2),
            "kelly_fraction": round(kelly_fraction, 4),
        })
        total_kelly += kelly_fraction

    # 有効なオッズの馬がなかった場合は早期リターン
    if not allocations:
        return {"allocations": [], "strategy": "有効なオッズデータがないため配分不可"}

    # ケリー比率に基づいて配分
    if total_kelly > 0:
        for alloc in allocations:
            ratio = alloc["kelly_fraction"] / total_kelly
            raw_amount = total_budget * ratio
            # 100円単位に丸める
            alloc["suggested_amount"] = max(100, int(math.floor(raw_amount / 100) * 100))
            alloc["allocation_ratio"] = round(ratio * 100, 1)
    else:
        # ケリー基準で全馬マイナス期待値の場合
        equal_amount = max(100, int(math.floor(total_budget / len(allocations) / 100) * 100))
        for alloc in allocations:
            alloc["suggested_amount"] = equal_amount
            alloc["allocation_ratio"] = round(100 / len(allocations), 1)

    # 配分合計を算出
    total_allocated = sum(a["suggested_amount"] for a in allocations)

    # 100円単位への丸めにより発生した残額を、期待値が最も高い馬に再配分する
    remaining_budget = total_budget - total_allocated
    if allocations and remaining_budget >= 100:
        extra_amount = int(math.floor(remaining_budget / 100) * 100)
        if extra_amount >= 100:
            best_allocation = max(allocations, key=lambda x: x["expected_return"])
            best_allocation["suggested_amount"] += extra_amount
            total_allocated = sum(a["suggested_amount"] for a in allocations)

    strategy_parts = []
    ev_positive = [a for a in allocations if a["expected_return"] >= 1.0]
    if ev_positive:
        best = max(ev_positive, key=lambda x: x["expected_return"])
        strategy_parts.append(
            f"{best['horse_number']}番に重点配分（期待値{best['expected_return']}）"
        )
    ev_negative = [a for a in allocations if a["expected_return"] < 0.8]
    if ev_negative:
        worst = min(ev_negative, key=lambda x: x["expected_return"])
        strategy_parts.append(
            f"{worst['horse_number']}番は期待値{worst['expected_return']}で配分を抑制"
        )
    if not strategy_parts:
        strategy_parts.append("各馬の期待値に基づく均等配分")

    return {
        "allocations": allocations,
        "total_allocated": total_allocated,
        "strategy": "。".join(strategy_parts),
    }


def _analyze_bet_selection_impl(
    race_id: str,
    bet_type: str,
    horse_numbers: list[int],
    amount: int,
    runners_data: list[dict],
    race_conditions: list[str] | None = None,
    ai_predictions: list[dict] | None = None,
) -> dict:
    """買い目分析の実装（テスト用に公開）."""
    selected_horses = [
        r for r in runners_data if r.get("horse_number") in horse_numbers
    ]

    if not selected_horses:
        return {
            "error": "選択された馬番に該当する馬が見つかりませんでした",
            "horse_numbers": horse_numbers,
        }

    total_runners = len(runners_data)

    # オッズと人気の集計
    odds_list = [h.get("odds", 0) or 0 for h in selected_horses]
    popularity_list = [h.get("popularity", 0) or 0 for h in selected_horses]

    avg_odds = sum(odds_list) / len(odds_list) if odds_list else 0
    avg_popularity = sum(popularity_list) / len(popularity_list) if popularity_list else 0

    # 人気馬の判定（3番人気以内）
    popular_horses = [h for h in selected_horses if (h.get("popularity") or 99) <= 3]
    # 穴馬の判定（10番人気以下）
    longshot_horses = [h for h in selected_horses if (h.get("popularity") or 99) >= 10]

    # 各馬の期待値分析（券種・頭数・条件を考慮）
    horse_analysis = []
    for h in selected_horses:
        odds = h.get("odds") or 0
        pop = h.get("popularity") or 99
        ev = _calculate_expected_value(
            odds, pop, bet_type, total_runners, race_conditions
        )
        horse_analysis.append({
            "horse_number": h.get("horse_number"),
            "horse_name": h.get("horse_name"),
            "odds": odds,
            "popularity": pop,
            "expected_value": ev,
        })

    # 組み合わせ馬券の確率推定
    combination_prob = _calculate_combination_probability(
        popularity_list, bet_type, total_runners, race_conditions
    )

    # 弱点分析
    weaknesses = _analyze_weaknesses(
        selected_horses, bet_type, total_runners, race_conditions
    )

    # トリガミリスク計算（従来方式）
    torigami_risk = _calculate_torigami_risk(bet_type, selected_horses, amount)

    # 合成オッズ計算（複数買い目の場合）
    composite_odds = _calculate_composite_odds(odds_list)
    if composite_odds["torigami_warning"]:
        weaknesses.append(composite_odds["torigami_warning"])

    # AI指数内訳コンテキスト
    ai_context = _analyze_ai_index_context(ai_predictions, horse_numbers)

    # 資金配分最適化（単勝・複勝で複数買いの場合）
    fund_allocation = _optimize_fund_allocation(
        selected_horses, amount, bet_type, total_runners, race_conditions
    )

    # 掛け金に対するフィードバック
    amount_feedback = _generate_amount_feedback(amount)

    return {
        "race_id": race_id,
        "bet_type": bet_type,
        "bet_type_name": BET_TYPE_NAMES.get(bet_type, bet_type),
        "total_runners": total_runners,
        "race_conditions": race_conditions or [],
        "selected_horses": horse_analysis,
        "combination_probability": combination_prob,
        "composite_odds": composite_odds,
        "ai_index_context": ai_context,
        "fund_allocation": fund_allocation,
        "summary": {
            "average_odds": round(avg_odds, 1),
            "average_popularity": round(avg_popularity, 1),
            "popular_horse_count": len(popular_horses),
            "longshot_horse_count": len(longshot_horses),
        },
        "weaknesses": weaknesses,
        "torigami_risk": torigami_risk,
        "amount": amount,
        "amount_feedback": amount_feedback,
    }


@tool
@log_tool_execution
def analyze_bet_selection(
    race_id: str,
    bet_type: str,
    horse_numbers: list[int],
    amount: int,
    runners_data: list[dict],
    race_conditions: list[str] | None = None,
    ai_predictions: list[dict] | None = None,
) -> dict:
    """買い目を分析し、データに基づくフィードバックを生成する.

    JRA統計に基づく券種別確率、出走頭数補正、レース条件補正を適用して
    期待値と弱点を分析する。合成オッズ計算、AI指数内訳分析、資金配分最適化も行う。

    Args:
        race_id: レースID
        bet_type: 券種 (win, place, quinella, quinella_place, exacta, trio, trifecta)
        horse_numbers: 選択した馬番のリスト
        amount: 掛け金
        runners_data: 出走馬データ（odds, popularity を含む）
        race_conditions: レース条件リスト
            - "handicap": ハンデ戦
            - "fillies_mares": 牝馬限定
            - "maiden_new": 新馬戦
            - "maiden": 未勝利戦
            - "g1": G1レース
            - "hurdle": 障害戦
        ai_predictions: AI予想データ（get_ai_predictionの結果）
            - horse_number: 馬番
            - score: AI指数
            - rank: AI順位
            - horse_name: 馬名

    Returns:
        分析結果:
        - selected_horses: 各馬の期待値分析
        - combination_probability: 組み合わせ的中確率の推定
        - composite_odds: 合成オッズ（トリガミ判定）
        - ai_index_context: AI指数の内訳コンテキスト
        - fund_allocation: 資金配分の提案
        - weaknesses: 弱点リスト
        - torigami_risk: トリガミリスク
    """
    return _analyze_bet_selection_impl(
        race_id, bet_type, horse_numbers, amount, runners_data,
        race_conditions, ai_predictions,
    )


def _generate_amount_feedback(amount: int) -> dict:
    """掛け金に対するフィードバックを生成する."""
    warnings = []
    info = []

    if amount >= 10000:
        warnings.append("1万円以上の掛け金は慎重にご検討ください")
    if amount >= 5000:
        info.append("高額の賭け金です。予算内での遊びをお勧めします")
    if amount % 100 != 0:
        info.append("馬券は100円単位での購入となります")

    return {
        "warnings": warnings,
        "info": info,
    }
