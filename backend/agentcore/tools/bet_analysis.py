"""買い目分析ツール.

選択された買い目を分析し、データに基づくフィードバックを生成する。
"""

from strands import tool

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

# JRA過去統計に基づく人気別勝率（単勝）
# 出典: JRA公式統計データ（概算値）
WIN_PROBABILITY_BY_POPULARITY = {
    1: 0.33,   # 1番人気: 約33%
    2: 0.19,   # 2番人気: 約19%
    3: 0.13,   # 3番人気: 約13%
    4: 0.09,   # 4番人気: 約9%
    5: 0.07,   # 5番人気: 約7%
    6: 0.05,   # 6番人気: 約5%
    7: 0.04,   # 7番人気: 約4%
    8: 0.03,   # 8番人気: 約3%
    9: 0.02,   # 9番人気: 約2%
    10: 0.02,  # 10番人気: 約2%
    11: 0.01,  # 11番人気以下: 約1%
    12: 0.01,
    13: 0.005,
    14: 0.005,
    15: 0.003,
    16: 0.003,
    17: 0.002,
    18: 0.002,
}


def _estimate_win_probability(popularity: int) -> float:
    """人気順から勝率を推定する（JRA過去統計ベース）.

    Args:
        popularity: 人気順位

    Returns:
        推定勝率（0.0-1.0）
    """
    if popularity <= 0:
        return 0.01
    return WIN_PROBABILITY_BY_POPULARITY.get(popularity, 0.002)


def _calculate_expected_value(odds: float, popularity: int) -> dict:
    """期待値を計算する.

    Args:
        odds: オッズ
        popularity: 人気順位

    Returns:
        期待値分析結果
    """
    if odds <= 0:
        return {
            "estimated_probability": 0,
            "expected_return": 0,
            "value_rating": "データ不足",
        }

    estimated_prob = _estimate_win_probability(popularity)
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

    return {
        "estimated_probability": round(estimated_prob * 100, 1),  # パーセント表示
        "expected_return": round(expected_return, 2),
        "value_rating": rating,
    }


def _analyze_weaknesses(
    selected_horses: list[dict],
    bet_type: str,
    total_runners: int,
) -> list[str]:
    """買い目の弱点を分析する.

    Args:
        selected_horses: 選択された馬のリスト
        bet_type: 券種
        total_runners: 出走頭数

    Returns:
        弱点リスト
    """
    weaknesses = []

    if not selected_horses:
        return weaknesses

    popularities = [h.get("popularity") or 99 for h in selected_horses]
    odds_list = [h.get("odds") or 0 for h in selected_horses]

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
            odds = h.get("odds") or 0
            prob = _estimate_win_probability(pop)
            weaknesses.append(
                f"{h.get('horse_number')}番 {h.get('horse_name')}は最下位人気。"
                f"統計的勝率は約{prob*100:.1f}%"
            )

    # 4. 1番人気依存チェック
    has_favorite = any(p == 1 for p in popularities)
    if has_favorite and bet_type in ("trio", "trifecta", "quinella", "exacta"):
        weaknesses.append(
            "1番人気を軸にした買い目。JRA統計では1番人気の勝率は約33%、"
            "つまり67%は外れる"
        )

    # 5. 三連系のトリガミリスク
    if bet_type in ("trio", "trifecta") and len(selected_horses) >= 3:
        avg_pop = sum(popularities) / len(popularities)
        if avg_pop <= 3:
            weaknesses.append(
                "三連系で人気馬中心の組み合わせ。"
                "的中してもトリガミ（配当が投資額以下）の可能性大"
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
        }

    # 単勝・複勝の場合は最低オッズで計算
    if bet_type in ("win", "place"):
        min_odds = min(h.get("odds") or 999 for h in selected_horses)
        estimated_return = int(min_odds * 100)  # 100円あたりの配当

        if bet_type == "place":
            # 複勝はオッズが低い（単勝の約1/3程度と仮定）
            estimated_return = int(estimated_return * 0.4)

        is_torigami = estimated_return < amount
        risk_level = "高" if is_torigami else "低"

        return {
            "risk_level": risk_level,
            "estimated_min_return": estimated_return,
            "is_torigami_likely": is_torigami,
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
    }


def _analyze_bet_selection_impl(
    race_id: str,
    bet_type: str,
    horse_numbers: list[int],
    amount: int,
    runners_data: list[dict],
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
    longshot_horses = [h for h in selected_horses if (h.get("popularity") or 0) >= 10]

    # 各馬の期待値分析
    horse_analysis = []
    for h in selected_horses:
        odds = h.get("odds") or 0
        pop = h.get("popularity") or 99
        ev = _calculate_expected_value(odds, pop)
        horse_analysis.append({
            "horse_number": h.get("horse_number"),
            "horse_name": h.get("horse_name"),
            "odds": odds,
            "popularity": pop,
            "expected_value": ev,
        })

    # 弱点分析
    weaknesses = _analyze_weaknesses(selected_horses, bet_type, total_runners)

    # トリガミリスク計算
    torigami_risk = _calculate_torigami_risk(bet_type, selected_horses, amount)

    # 掛け金に対するフィードバック
    amount_feedback = _generate_amount_feedback(amount)

    return {
        "race_id": race_id,
        "bet_type": bet_type,
        "bet_type_name": BET_TYPE_NAMES.get(bet_type, bet_type),
        "total_runners": total_runners,
        "selected_horses": horse_analysis,
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
def analyze_bet_selection(
    race_id: str,
    bet_type: str,
    horse_numbers: list[int],
    amount: int,
    runners_data: list[dict],
) -> dict:
    """買い目を分析し、データに基づくフィードバックを生成する.

    Args:
        race_id: レースID
        bet_type: 券種 (win, place, quinella, quinella_place, exacta, trio, trifecta)
        horse_numbers: 選択した馬番のリスト
        amount: 掛け金
        runners_data: 出走馬データ

    Returns:
        分析結果（選択馬のオッズ、人気、期待値、弱点など）
    """
    return _analyze_bet_selection_impl(
        race_id, bet_type, horse_numbers, amount, runners_data
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
