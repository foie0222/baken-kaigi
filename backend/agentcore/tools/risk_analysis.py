"""リスク分析・心理バイアス対策ツール.

買い目のリスクシナリオ、除外馬分析、バイアス診断、見送り推奨、ニアミス分析を統合。
"""

from strands import tool

from .bet_analysis import (
    WIN_RATE_BY_POPULARITY,
    _estimate_probability,
)
from .common import log_tool_execution
from .constants import (
    AI_SCORE_CLOSE_GAP,
    AI_SCORE_MODERATE_GAP,
    FAVORITE_BIAS_RATIO,
    HIGH_PAYOUT_TYPE_RATIO,
    LONGSHOT_BIAS_RATIO,
    OVER_INVESTMENT_THRESHOLD,
)
from .pace_analysis import (
    _assess_race_difficulty,
    _analyze_odds_gap,
)


# =============================================================================
# Feature 4: 見送り推奨
# =============================================================================


def _assess_skip_recommendation(
    total_runners: int,
    race_conditions: list[str] | None = None,
    venue: str = "",
    runners_data: list[dict] | None = None,
    ai_predictions: list[dict] | None = None,
    predicted_pace: str = "",
) -> dict:
    """レースの見送り推奨度を判定する.

    pace_analysis._assess_race_difficulty()のスコアをベースに、
    AI予想のスコア分散とオッズ団子状態をチェックして総合判定する。

    Args:
        total_runners: 出走頭数
        race_conditions: レース条件リスト
        venue: 競馬場名
        runners_data: 出走馬データ
        ai_predictions: AI予想データ
        predicted_pace: 予想ペース

    Returns:
        見送り推奨結果（skip_score, recommendation, reasons）
    """
    race_conditions = race_conditions or []
    runners_data = runners_data or []
    ai_predictions = ai_predictions or []

    reasons = []
    skip_score = 0

    # 1. レース難易度ベーススコア（_assess_race_difficultyを再利用）
    difficulty = _assess_race_difficulty(
        total_runners, race_conditions, venue, runners_data
    )
    # difficulty_starsは1-5、スキップスコアに変換
    stars = difficulty["difficulty_stars"]
    if stars >= 5:
        skip_score += 4
        reasons.append(f"レース難易度★5（{difficulty['difficulty_label']}）")
    elif stars >= 4:
        skip_score += 3
        reasons.append(f"レース難易度★4（{difficulty['difficulty_label']}）")
    elif stars >= 3:
        skip_score += 1
    elif stars <= 2:
        skip_score -= 1

    # 2. AI予想のスコア分散（上位混戦チェック）
    if ai_predictions:
        sorted_preds = sorted(
            ai_predictions, key=lambda x: x.get("score", 0), reverse=True
        )
        if len(sorted_preds) >= 5:
            top5_scores = [p.get("score", 0) for p in sorted_preds[:5]]
            top_spread = top5_scores[0] - top5_scores[4]
            if top_spread <= AI_SCORE_CLOSE_GAP:
                skip_score += 3
                reasons.append(
                    f"AI上位5頭のスコア差が{top_spread}ptと僅差（混戦）"
                )
            elif top_spread <= AI_SCORE_MODERATE_GAP:
                skip_score += 1
                reasons.append(
                    f"AI上位5頭のスコア差が{top_spread}ptとやや接戦"
                )

    # 3. オッズ団子状態チェック
    if runners_data:
        odds_gap = _analyze_odds_gap(runners_data)
        if odds_gap and odds_gap["adjustment"] > 0:
            skip_score += 1
            reasons.append(odds_gap["comment"])

    # 4. 多頭数ボーナス
    if total_runners >= 16:
        skip_score += 1
        reasons.append(f"{total_runners}頭立ての多頭数レース")

    # 5. ハイペースボーナス（前が崩れやすく予測困難）
    if predicted_pace == "ハイ":
        skip_score += 1
        reasons.append("ハイペース予想で展開が読みにくい")

    # スコアを0-10に収める
    skip_score = max(0, min(10, skip_score))

    # 推奨判定
    if skip_score >= 7:
        recommendation = "見送り推奨"
    elif skip_score >= 5:
        recommendation = "慎重に検討"
    else:
        recommendation = "通常判断"

    return {
        "skip_score": skip_score,
        "recommendation": recommendation,
        "reasons": reasons,
        "difficulty": difficulty,
    }


# =============================================================================
# Feature 2: 除外馬リスク分析
# =============================================================================


def _analyze_excluded_horses(
    runners_data: list[dict],
    horse_numbers: list[int],
    ai_predictions: list[dict] | None = None,
    total_runners: int = 18,
) -> dict:
    """選択外の上位人気・AI上位馬のリスクを分析する.

    Args:
        runners_data: 出走馬データ
        horse_numbers: 選択された馬番リスト
        ai_predictions: AI予想データ
        total_runners: 出走頭数

    Returns:
        除外馬リスク分析結果（excluded_horses）
    """
    ai_predictions = ai_predictions or []
    selected_set = set(horse_numbers)

    # AI順位マッピング
    ai_rank_map = {}
    for pred in ai_predictions:
        ai_rank_map[pred.get("horse_number")] = pred.get("rank", 99)

    excluded = []
    for runner in runners_data:
        hn = runner.get("horse_number")
        if hn in selected_set:
            continue

        popularity = runner.get("popularity") or 99
        ai_rank = ai_rank_map.get(hn, 99)

        # 上位人気（5番人気以内）またはAI上位（5位以内）のみを対象
        if popularity > 5 and ai_rank > 5:
            continue

        # 勝率計算（_estimate_probabilityを再利用）
        win_prob = _estimate_probability(popularity, "win", total_runners)
        place_prob = _estimate_probability(popularity, "place", total_runners)

        # 危険度判定
        if popularity <= 2 or ai_rank <= 2:
            danger_level = "high"
        elif popularity <= 4 or ai_rank <= 4:
            danger_level = "medium"
        else:
            danger_level = "low"

        horse_name = runner.get("horse_name", "")
        comment = f"もし{hn}番{horse_name}が来ても、それは確率{win_prob*100:.1f}%の事象"

        excluded.append({
            "horse_number": hn,
            "horse_name": horse_name,
            "popularity": popularity,
            "ai_rank": ai_rank,
            "win_probability": round(win_prob * 100, 1),
            "place_probability": round(place_prob * 100, 1),
            "danger_level": danger_level,
            "comment": comment,
        })

    # 危険度順にソート（勝率降順）
    excluded.sort(key=lambda x: x["win_probability"], reverse=True)

    # 上位5頭まで
    excluded = excluded[:5]

    return {
        "excluded_horses": excluded,
    }


# =============================================================================
# Feature 1: リスクシナリオ提示
# =============================================================================


def _generate_risk_scenarios(
    runners_data: list[dict],
    horse_numbers: list[int],
    ai_predictions: list[dict] | None = None,
    predicted_pace: str = "",
    race_conditions: list[str] | None = None,
) -> dict:
    """買い目が外れるパターンを2-3シナリオで生成する.

    Args:
        runners_data: 出走馬データ
        horse_numbers: 選択された馬番リスト
        ai_predictions: AI予想データ
        predicted_pace: 予想ペース
        race_conditions: レース条件リスト

    Returns:
        リスクシナリオ結果（scenarios）
    """
    ai_predictions = ai_predictions or []
    race_conditions = race_conditions or []
    scenarios = []

    if not runners_data and not horse_numbers:
        return {"scenarios": []}

    selected_set = set(horse_numbers)

    # 選択馬の情報を取得
    selected_runners = [
        r for r in runners_data if r.get("horse_number") in selected_set
    ]
    selected_popularities = [r.get("popularity") or 99 for r in selected_runners]

    # --- 前崩れシナリオ ---
    if predicted_pace == "ハイ":
        # 選択馬に先行型がいるかチェック（人気上位=先行しがちと仮定）
        scenarios.append({
            "type": "前崩れ",
            "description": "ハイペースで前が総崩れするシナリオ",
            "detail": "逃げ・先行馬が3頭以上でハイペース予想。"
                      "前が潰れて差し・追込馬が台頭する展開",
            "risk_for_selection": "選択馬に先行脚質がいる場合、"
                                 "展開不利で大きく着順を下げる可能性",
        })

    # --- 穴馬番狂わせシナリオ ---
    if ai_predictions:
        ai_top3_numbers = {
            p.get("horse_number")
            for p in sorted(ai_predictions, key=lambda x: x.get("rank", 99))[:3]
        }
        excluded_ai_top = ai_top3_numbers - selected_set
        if excluded_ai_top:
            runners_map = {r.get("horse_number"): r for r in runners_data}
            excluded_names = [
                f"{hn}番{runners_map[hn].get('horse_name', '')}"
                for hn in excluded_ai_top
                if hn in runners_map
            ]
            scenarios.append({
                "type": "穴馬番狂わせ",
                "description": "AI上位馬が激走するシナリオ",
                "detail": f"AI上位の{', '.join(excluded_names)}が選択外。"
                          "市場が見落とした馬が激走する可能性",
                "risk_for_selection": "AI評価が高い馬を外しているため、"
                                     "予想外の結果になるリスクあり",
            })

    # --- 本命飛びシナリオ ---
    has_favorite = any(p == 1 for p in selected_popularities)
    if has_favorite:
        win_rate = WIN_RATE_BY_POPULARITY.get(1, 0.33)
        scenarios.append({
            "type": "本命飛び",
            "description": "1番人気が凡走するシナリオ",
            "detail": f"JRA統計では1番人気の勝率は約{win_rate*100:.0f}%。"
                      f"つまり{(1-win_rate)*100:.0f}%の確率で勝てない",
            "risk_for_selection": "1番人気を軸にした買い目は、"
                                 "本命が飛ぶと全滅リスクが高い",
        })

    # --- 荒れレースシナリオ ---
    upset_conditions = {"handicap", "maiden_new", "hurdle"}
    active_upsets = set(race_conditions) & upset_conditions
    if active_upsets:
        condition_names = {
            "handicap": "ハンデ戦",
            "maiden_new": "新馬戦",
            "hurdle": "障害戦",
        }
        names = [condition_names.get(c, c) for c in active_upsets]
        scenarios.append({
            "type": "荒れレース",
            "description": f"{'/'.join(names)}で波乱が起きるシナリオ",
            "detail": f"{'/'.join(names)}は人気馬の信頼度が低く、波乱含みのレース条件",
            "risk_for_selection": "人気馬中心の買い目は条件的に荒れるリスクが高い",
        })

    # 2-3件に制限
    if len(scenarios) > 3:
        scenarios = scenarios[:3]

    # 最低2件を確保（足りない場合はジェネリックシナリオを追加）
    if len(scenarios) < 2 and runners_data:
        if not has_favorite and "本命飛び" not in [s["type"] for s in scenarios]:
            fav_runner = next(
                (r for r in runners_data if r.get("popularity") == 1), None
            )
            if fav_runner:
                scenarios.append({
                    "type": "本命飛び",
                    "description": "1番人気が凡走するシナリオ",
                    "detail": f"{fav_runner.get('horse_name', '')}が1番人気だが、"
                              f"JRA統計では約67%の確率で勝てない",
                    "risk_for_selection": "1番人気の結果次第で配当が大きく変動",
                })
        if len(scenarios) < 2:
            scenarios.append({
                "type": "不測の事態",
                "description": "出走取消・落馬など予測不能な事象",
                "detail": "出走取消、落馬、競走中止など予測不能な事象が発生する可能性",
                "risk_for_selection": "どの買い目でも起こりうるリスク",
            })

    return {"scenarios": scenarios}


# =============================================================================
# Feature 3: バイアス診断
# =============================================================================


def _diagnose_betting_bias(cart_items: list[dict]) -> dict:
    """カート内の買い目からセッションレベルのバイアスを検出する.

    Args:
        cart_items: カート全体のデータ

    Returns:
        バイアス診断結果（biases）
    """
    if not cart_items:
        return {"biases": []}

    biases = []

    # 全選択馬の人気を収集
    all_popularities = []
    for item in cart_items:
        runners_data = item.get("runners_data", [])
        horse_numbers = item.get("horseNumbers", [])
        runners_map = {r.get("horse_number"): r for r in runners_data}
        for hn in horse_numbers:
            runner = runners_map.get(hn)
            if runner:
                pop = runner.get("popularity") or 99
                all_popularities.append(pop)

    # 券種を収集
    all_bet_types = [item.get("betType", "") for item in cart_items]

    # 合計金額
    total_amount = sum(item.get("amount", 0) for item in cart_items)

    # --- 穴馬偏重チェック ---
    if all_popularities:
        longshot_count = sum(1 for p in all_popularities if p >= 10)
        longshot_ratio = longshot_count / len(all_popularities)
        if longshot_ratio >= LONGSHOT_BIAS_RATIO:
            biases.append({
                "type": "穴馬偏重",
                "description": f"選択馬の{longshot_ratio*100:.0f}%が10番人気以下。"
                               "的中率が極めて低い構成",
                "suggestion": "上位人気馬を軸に加えてバランスを取ることを検討",
            })

    # --- 本命偏重チェック ---
    if all_popularities:
        fav_count = sum(1 for p in all_popularities if p <= 3)
        fav_ratio = fav_count / len(all_popularities)
        if fav_ratio >= FAVORITE_BIAS_RATIO and len(all_popularities) >= 3:
            biases.append({
                "type": "本命偏重",
                "description": f"選択馬の{fav_ratio*100:.0f}%が3番人気以内。"
                               "配当が低くトリガミリスクが高い",
                "suggestion": "中穴馬を1頭加えて配当を上げることを検討",
            })

    # --- 高配当券種偏重チェック ---
    if all_bet_types:
        high_payout_types = {"trio", "trifecta"}
        high_count = sum(1 for bt in all_bet_types if bt in high_payout_types)
        high_ratio = high_count / len(all_bet_types)
        if high_ratio >= HIGH_PAYOUT_TYPE_RATIO and len(all_bet_types) >= 2:
            biases.append({
                "type": "高配当券種偏重",
                "description": f"買い目の{high_ratio*100:.0f}%が三連単/三連複。"
                               "的中難度が非常に高い",
                "suggestion": "馬連やワイドなど的中しやすい券種も混ぜることを検討",
            })

    # --- 過大投資チェック ---
    if total_amount >= OVER_INVESTMENT_THRESHOLD:
        biases.append({
            "type": "過大投資",
            "description": f"合計投資額が¥{total_amount:,}。"
                           "予算を超えた投資は精神的に不利",
            "suggestion": "予算を決めて、その範囲内で楽しむことを推奨",
        })

    return {"biases": biases}


# =============================================================================
# Feature 5: ニアミス分析（スタブ）
# =============================================================================


def _analyze_near_miss(
    race_id: str,
    horse_numbers: list[int],
    bet_type: str,
) -> dict:
    """ニアミス分析（スタブ）.

    レース結果APIが未実装のためスタブ関数。
    将来の拡張ポイントとして関数シグネチャのみ定義。

    Args:
        race_id: レースID
        horse_numbers: 選択した馬番リスト
        bet_type: 券種

    Returns:
        スタブメッセージ
    """
    return {
        "status": "unavailable",
        "message": "レース結果確定後に利用可能になります。"
                   "現在はレース結果APIが未実装のため、この機能はご利用いただけません。",
        "race_id": race_id,
    }


# =============================================================================
# 統合関数
# =============================================================================


def _analyze_risk_factors_impl(
    race_id: str,
    horse_numbers: list[int],
    runners_data: list[dict],
    ai_predictions: list[dict] | None = None,
    predicted_pace: str = "",
    race_conditions: list[str] | None = None,
    venue: str = "",
    total_runners: int = 18,
    cart_items: list[dict] | None = None,
) -> dict:
    """リスク分析の統合実装（テスト用に公開）.

    Args:
        race_id: レースID
        horse_numbers: 選択した馬番リスト
        runners_data: 出走馬データ
        ai_predictions: AI予想データ
        predicted_pace: 予想ペース
        race_conditions: レース条件リスト
        venue: 競馬場名
        total_runners: 出走頭数
        cart_items: カートデータ

    Returns:
        5つの分析結果を統合した辞書
    """
    race_conditions = race_conditions or []
    cart_items = cart_items or []

    # 1. リスクシナリオ
    risk_scenarios = _generate_risk_scenarios(
        runners_data=runners_data,
        horse_numbers=horse_numbers,
        ai_predictions=ai_predictions,
        predicted_pace=predicted_pace,
        race_conditions=race_conditions,
    )

    # 2. 除外馬分析
    excluded_horses = _analyze_excluded_horses(
        runners_data=runners_data,
        horse_numbers=horse_numbers,
        ai_predictions=ai_predictions,
        total_runners=total_runners,
    )

    # 3. 見送り推奨
    skip_recommendation = _assess_skip_recommendation(
        total_runners=total_runners,
        race_conditions=race_conditions,
        venue=venue,
        runners_data=runners_data,
        ai_predictions=ai_predictions,
        predicted_pace=predicted_pace,
    )

    # 4. バイアス診断
    betting_bias = _diagnose_betting_bias(cart_items)

    # 5. ニアミス分析（スタブ）
    near_miss = _analyze_near_miss(
        race_id=race_id,
        horse_numbers=horse_numbers,
        bet_type="",
    )

    return {
        "race_id": race_id,
        "risk_scenarios": risk_scenarios,
        "excluded_horses": excluded_horses,
        "skip_recommendation": skip_recommendation,
        "betting_bias": betting_bias,
        "near_miss": near_miss,
    }


@tool
@log_tool_execution
def analyze_risk_factors(
    race_id: str,
    horse_numbers: list[int],
    runners_data: list[dict],
    total_runners: int,
    ai_predictions: list[dict] | None = None,
    predicted_pace: str = "",
    race_conditions: list[str] | None = None,
    venue: str = "",
    cart_items: list[dict] | None = None,
) -> dict:
    """買い目のリスク分析・心理バイアス対策を行う.

    5つの分析を統合して実行する:
    1. リスクシナリオ提示: 買い目が外れるパターンを2-3シナリオで提示
    2. 除外馬リスク分析: 選択外の上位馬に「外す理由」と「勝つ確率」を提示
    3. バイアス診断: カート全体の偏り（穴馬偏重、本命偏重等）を検出
    4. 見送り推奨: レース条件・AI混戦度から見送りスコアを算出
    5. ニアミス分析: レース結果確定後に利用可能（現在はスタブ）

    Args:
        race_id: レースID
        horse_numbers: 選択した馬番のリスト
        runners_data: 出走馬データ（odds, popularity を含む）
        total_runners: 出走頭数
        ai_predictions: AI予想データ（get_ai_predictionの結果）
        predicted_pace: 予想ペース（"ハイ", "ミドル", "スロー"）
            analyze_race_characteristicsの結果から取得
        race_conditions: レース条件リスト
        venue: 競馬場名
        cart_items: カートデータ（バイアス診断に使用）

    Returns:
        統合分析結果:
        - risk_scenarios: リスクシナリオ（2-3件）
        - excluded_horses: 除外馬リスク（上位5頭）
        - skip_recommendation: 見送り推奨（スコア0-10、7以上で見送り推奨）
        - betting_bias: バイアス診断（穴馬偏重、本命偏重、高配当券種偏重、過大投資）
        - near_miss: ニアミス分析（現在はスタブ）
    """
    return _analyze_risk_factors_impl(
        race_id=race_id,
        horse_numbers=horse_numbers,
        runners_data=runners_data,
        ai_predictions=ai_predictions,
        predicted_pace=predicted_pace,
        race_conditions=race_conditions,
        venue=venue,
        total_runners=total_runners,
        cart_items=cart_items,
    )
