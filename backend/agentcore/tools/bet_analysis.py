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


@tool
def analyze_bet_selection(
    race_id: str,
    bet_type: str,
    horse_numbers: list[int],
    amount: int,
    runners_data: list[dict],
) -> dict:
    """買い目を分析し、データに基づくフィードバックを生成する。

    Args:
        race_id: レースID
        bet_type: 券種 (win, place, quinella, quinella_place, exacta, trio, trifecta)
        horse_numbers: 選択した馬番のリスト
        amount: 掛け金
        runners_data: 出走馬データ

    Returns:
        分析結果（選択馬のオッズ、人気、期待値など）
    """
    selected_horses = [
        r for r in runners_data if r.get("horse_number") in horse_numbers
    ]

    if not selected_horses:
        return {
            "error": "選択された馬番に該当する馬が見つかりませんでした",
            "horse_numbers": horse_numbers,
        }

    # オッズと人気の集計
    odds_list = [h.get("odds", 0) or 0 for h in selected_horses]
    popularity_list = [h.get("popularity", 0) or 0 for h in selected_horses]

    avg_odds = sum(odds_list) / len(odds_list) if odds_list else 0
    avg_popularity = sum(popularity_list) / len(popularity_list) if popularity_list else 0

    # 人気馬の判定（3番人気以内）
    popular_horses = [h for h in selected_horses if (h.get("popularity") or 99) <= 3]
    # 穴馬の判定（10番人気以下）
    longshot_horses = [h for h in selected_horses if (h.get("popularity") or 0) >= 10]

    # 掛け金に対するフィードバック
    amount_feedback = _generate_amount_feedback(amount)

    return {
        "race_id": race_id,
        "bet_type": bet_type,
        "bet_type_name": BET_TYPE_NAMES.get(bet_type, bet_type),
        "selected_horses": [
            {
                "horse_number": h.get("horse_number"),
                "horse_name": h.get("horse_name"),
                "odds": h.get("odds"),
                "popularity": h.get("popularity"),
            }
            for h in selected_horses
        ],
        "summary": {
            "average_odds": round(avg_odds, 1),
            "average_popularity": round(avg_popularity, 1),
            "popular_horse_count": len(popular_horses),
            "longshot_horse_count": len(longshot_horses),
        },
        "amount": amount,
        "amount_feedback": amount_feedback,
    }


def _generate_amount_feedback(amount: int) -> dict:
    """掛け金に対するフィードバックを生成する。"""
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
