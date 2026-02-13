"""オッズ変動分析ツール.

オッズの変動パターンを分析し、市場の動向を読み解くツール。
AI指数ベースの妙味分析、時間帯別変動分析、単複比分析を含む。
"""

import math

from strands import tool

from .common import get_tool_logger, log_tool_execution
from .constants import (
    AI_VALUE_HIGH,
    AI_VALUE_LOW,
    ODDS_DROP,
    ODDS_RISE,
    ODDS_SHARP_DROP,
    ODDS_SHARP_RISE,
    WIN_PLACE_RATIO_HIGH,
    WIN_PLACE_RATIO_LOW,
)
from . import odds_client

logger = get_tool_logger("odds_analysis")


@tool
@log_tool_execution
def analyze_odds_movement(
    race_id: str,
    horse_numbers: list[int] | None = None,
    ai_predictions: list[dict] | None = None,
) -> dict:
    """オッズの変動パターンを分析する。

    AI指数ベースの妙味分析、時間帯別変動分析、単複比分析を行う。

    Args:
        race_id: レースID
        horse_numbers: 特定馬のみ分析する場合は馬番リスト
        ai_predictions: AI予想データ（get_ai_predictionの結果）
            - horse_number: 馬番
            - score: AI指数
            - rank: AI順位

    Returns:
        分析結果:
        - market_overview: 市場概要
        - movements: オッズ変動分析
        - time_based_analysis: 時間帯別変動分析
        - value_analysis: AI指数ベースの妙味分析
        - win_place_ratio_analysis: 単複比分析
        - betting_patterns: 投票パターン分析
    """
    try:
        odds_history = odds_client.get_odds_history(race_id)

        if not odds_history:
            return {
                "warning": "オッズ履歴がありません",
                "race_id": race_id,
            }

        # 以下のコードは odds_history がある場合のみ到達
        # 複勝オッズを取得（単複比分析用）
        place_odds = _fetch_place_odds(race_id)

        # 市場概要
        market_overview = _analyze_market_overview(odds_history)

        # 馬ごとの変動分析
        movements = _analyze_movements(odds_history, horse_numbers)

        # 時間帯別変動分析
        time_based_analysis = _analyze_time_based_movements(
            odds_history, horse_numbers
        )

        # AI指数ベースの妙味分析
        value_analysis = _analyze_value_with_ai(
            odds_history, horse_numbers, ai_predictions
        )

        # 単複比分析
        win_place_ratio_analysis = _analyze_win_place_ratio(
            odds_history, place_odds, horse_numbers
        )

        # 投票パターン分析
        betting_patterns = _analyze_betting_patterns(
            movements, time_based_analysis
        )

        # 総合コメント生成
        overall_comment = _generate_odds_comment(
            movements, time_based_analysis, value_analysis,
            win_place_ratio_analysis, betting_patterns
        )

        return {
            "race_id": race_id,
            "market_overview": market_overview,
            "movements": movements,
            "time_based_analysis": time_based_analysis,
            "value_analysis": value_analysis,
            "win_place_ratio_analysis": win_place_ratio_analysis,
            "betting_patterns": betting_patterns,
            "overall_comment": overall_comment,
        }
    except Exception as e:
        logger.error(f"Failed to analyze odds movement: {e}")
        return {"error": str(e)}


def _fetch_place_odds(race_id: str) -> list[dict]:
    """複勝オッズを取得する.

    Args:
        race_id: レースID

    Returns:
        複勝オッズリスト
    """
    win_odds = odds_client.get_win_odds(race_id)
    return [o for o in win_odds if o.get("type") == "place"]


def _analyze_market_overview(
    odds_history: list[dict],
) -> dict[str, dict | int | str | None]:
    """市場概要を分析する."""
    if not odds_history:
        return {
            "favorite": None,
            "total_pool": 0,
            "market_confidence": "不明",
        }

    latest = odds_history[-1] if odds_history else {}
    odds_list = latest.get("odds", [])

    if not odds_list:
        return {
            "favorite": None,
            "total_pool": 0,
            "market_confidence": "不明",
        }

    # 1番人気を特定
    sorted_odds = sorted(odds_list, key=lambda x: x.get("odds", 999))
    favorite = sorted_odds[0] if sorted_odds else None

    # 市場信頼度（1番人気のオッズから判定）
    fav_odds = favorite.get("odds", 10.0) if favorite else 10.0
    if fav_odds <= 2.0:
        market_confidence = "非常に高い"
    elif fav_odds <= 3.5:
        market_confidence = "高い"
    elif fav_odds <= 5.0:
        market_confidence = "普通"
    else:
        market_confidence = "低い（混戦）"

    return {
        "favorite": {
            "horse_number": favorite.get("horse_number", 0),
            "horse_name": favorite.get("horse_name", ""),
            "odds": fav_odds,
        } if favorite else None,
        "total_pool": latest.get("total_pool", 0),
        "market_confidence": market_confidence,
    }


def _analyze_movements(
    odds_history: list[dict],
    horse_numbers: list[int] | None,
) -> list[dict[str, str | int | float]]:
    """馬ごとのオッズ変動を分析する."""
    if len(odds_history) < 2:
        return []

    initial = odds_history[0]
    latest = odds_history[-1]

    initial_odds = {o.get("horse_number"): o for o in initial.get("odds", [])}
    latest_odds = {o.get("horse_number"): o for o in latest.get("odds", [])}

    movements = []
    for horse_num, latest_data in latest_odds.items():
        if horse_numbers and horse_num not in horse_numbers:
            continue

        initial_data = initial_odds.get(horse_num, {})
        init_odds = initial_data.get("odds", 0)
        curr_odds = latest_data.get("odds", 0)

        if init_odds <= 0 or curr_odds <= 0:
            continue

        change_rate = ((curr_odds - init_odds) / init_odds) * 100

        # トレンド判定
        if change_rate <= ODDS_SHARP_DROP:
            trend = "急落"
            movement_type = "大口投票の可能性"
            alert_level = "要注目"
        elif change_rate <= ODDS_DROP:
            trend = "下落"
            movement_type = "支持増加"
            alert_level = "注目"
        elif change_rate >= ODDS_SHARP_RISE:
            trend = "急騰"
            movement_type = "人気離散"
            alert_level = "要警戒"
        elif change_rate >= ODDS_RISE:
            trend = "上昇"
            movement_type = "人気やや下降"
            alert_level = "参考"
        else:
            trend = "安定"
            movement_type = "変動なし"
            alert_level = "普通"

        movements.append({
            "horse_number": horse_num,
            "horse_name": latest_data.get("horse_name", ""),
            "initial_odds": init_odds,
            "current_odds": curr_odds,
            "change_rate": round(change_rate, 1),
            "trend": trend,
            "movement_type": movement_type,
            "alert_level": alert_level,
        })

    # 変動率の大きい順にソート
    movements.sort(key=lambda x: abs(x.get("change_rate", 0)), reverse=True)
    return movements[:10]


def _analyze_time_based_movements(
    odds_history: list[dict],
    horse_numbers: list[int] | None,
) -> dict:
    """時間帯別のオッズ変動を分析する.

    締切前1時間の変動を特に重視する。

    Args:
        odds_history: オッズ履歴データ
        horse_numbers: 分析対象馬番リスト

    Returns:
        時間帯別変動分析結果
    """
    if len(odds_history) < 3:
        return {
            "final_hour_movements": [],
            "early_movements": [],
            "warning": "時間帯別分析には3つ以上のオッズデータが必要",
        }

    # 履歴を時刻でソート（タイムスタンプがあれば使用）
    # タイムスタンプがない場合は配列の後半を「締切前」とみなす
    total_entries = len(odds_history)
    final_hour_start_idx = max(0, total_entries - max(3, total_entries // 3))

    # 締切前1時間（概算）のデータ
    final_hour_data = odds_history[final_hour_start_idx:]
    early_data = odds_history[:final_hour_start_idx] if final_hour_start_idx > 0 else []

    final_hour_movements = []
    early_movements = []

    # 締切前の変動を分析
    if len(final_hour_data) >= 2:
        start = final_hour_data[0]
        end = final_hour_data[-1]

        start_odds = {o.get("horse_number"): o for o in start.get("odds", [])}
        end_odds = {o.get("horse_number"): o for o in end.get("odds", [])}

        for horse_num, end_data in end_odds.items():
            if horse_numbers and horse_num not in horse_numbers:
                continue

            start_data = start_odds.get(horse_num, {})
            s_odds = start_data.get("odds", 0)
            e_odds = end_data.get("odds", 0)

            if s_odds <= 0 or e_odds <= 0:
                continue

            change_rate = ((e_odds - s_odds) / s_odds) * 100

            if abs(change_rate) >= 10:  # 10%以上の変動のみ記録
                final_hour_movements.append({
                    "horse_number": horse_num,
                    "horse_name": end_data.get("horse_name", ""),
                    "change_rate": round(change_rate, 1),
                    "is_significant": abs(change_rate) >= 20,
                    "direction": "下落" if change_rate < 0 else "上昇",
                })

    # 序盤の変動を分析
    if len(early_data) >= 2:
        start = early_data[0]
        end = early_data[-1]

        start_odds = {o.get("horse_number"): o for o in start.get("odds", [])}
        end_odds = {o.get("horse_number"): o for o in end.get("odds", [])}

        for horse_num, end_data in end_odds.items():
            if horse_numbers and horse_num not in horse_numbers:
                continue

            start_data = start_odds.get(horse_num, {})
            s_odds = start_data.get("odds", 0)
            e_odds = end_data.get("odds", 0)

            if s_odds <= 0 or e_odds <= 0:
                continue

            change_rate = ((e_odds - s_odds) / s_odds) * 100

            if abs(change_rate) >= 15:  # 序盤は15%以上のみ
                early_movements.append({
                    "horse_number": horse_num,
                    "horse_name": end_data.get("horse_name", ""),
                    "change_rate": round(change_rate, 1),
                    "direction": "下落" if change_rate < 0 else "上昇",
                })

    # 締切前に急変した馬を特定（インサイダー疑惑）
    late_surge_horses = [
        m for m in final_hour_movements
        if m.get("is_significant") and m.get("direction") == "下落"
    ]

    return {
        "final_hour_movements": sorted(
            final_hour_movements,
            key=lambda x: abs(x.get("change_rate", 0)),
            reverse=True,
        )[:5],
        "early_movements": sorted(
            early_movements,
            key=lambda x: abs(x.get("change_rate", 0)),
            reverse=True,
        )[:5],
        "late_surge_horses": late_surge_horses,
        "analysis_note": "締切前の急変は関係者情報の可能性あり" if late_surge_horses else None,
    }


def _analyze_value_with_ai(
    odds_history: list[dict],
    horse_numbers: list[int] | None,
    ai_predictions: list[dict] | None,
) -> list[dict]:
    """AI指数ベースの妙味分析を行う.

    Args:
        odds_history: オッズ履歴データ
        horse_numbers: 分析対象馬番リスト
        ai_predictions: AI予想データ

    Returns:
        妙味分析結果のリスト
    """
    if not odds_history:
        return []

    latest = odds_history[-1]
    odds_list = latest.get("odds", [])

    # AI予想を馬番でインデックス化
    ai_data = {}
    if ai_predictions:
        for pred in ai_predictions:
            ai_data[pred.get("horse_number")] = pred

    value_horses = []
    for o in odds_list:
        horse_num = o.get("horse_number", 0)
        if horse_numbers and horse_num not in horse_numbers:
            continue

        curr_odds = o.get("odds", 0)
        if curr_odds <= 0:
            continue

        # AI指数から適正オッズを推定
        ai_pred = ai_data.get(horse_num)
        if ai_pred:
            ai_score = ai_pred.get("score", 0)
            ai_rank = ai_pred.get("rank", 99)
            estimated_fair_odds = _estimate_fair_odds_from_ai(ai_score, ai_rank)
            estimation_method = "AI指数"
        else:
            # AI指数がない場合は警告付きでフォールバック
            popularity = o.get("popularity", 10)
            estimated_fair_odds = _estimate_fair_odds_fallback(popularity)
            estimation_method = "人気順（参考値）"

        if estimated_fair_odds <= 0:
            continue

        value_ratio = curr_odds / estimated_fair_odds

        if value_ratio >= AI_VALUE_HIGH:
            value_rating = "妙味あり"
            if ai_pred:
                comment = f"AI{ai_pred.get('rank')}位だがオッズ高い。市場が過小評価"
            else:
                comment = "オッズが高め。穴候補の可能性"
        elif value_ratio <= AI_VALUE_LOW:
            value_rating = "過剰人気"
            if ai_pred:
                comment = f"AI{ai_pred.get('rank')}位に対しオッズ低い。過剰人気"
            else:
                comment = "人気先行。オッズが低すぎる"
        else:
            value_rating = "適正"
            comment = "オッズは実力相応"

        # 妙味ありと過剰人気のみ返却
        if value_rating != "適正":
            value_horses.append({
                "horse_number": horse_num,
                "horse_name": o.get("horse_name", ""),
                "current_odds": curr_odds,
                "estimated_fair_odds": round(estimated_fair_odds, 1),
                "value_ratio": round(value_ratio, 2),
                "value_rating": value_rating,
                "estimation_method": estimation_method,
                "ai_rank": ai_pred.get("rank") if ai_pred else None,
                "comment": comment,
            })

    # 妙味ありを優先、その後過剰人気
    value_horses.sort(
        key=lambda x: (0 if x.get("value_rating") == "妙味あり" else 1, -x.get("value_ratio", 0))
    )
    return value_horses[:8]


_AI_SCORE_ODDS_ANCHORS = [
    (400, 2.0), (300, 3.0), (250, 4.0), (200, 5.0),
    (150, 8.0), (100, 15.0), (50, 30.0), (0, 50.0),
]


def _estimate_fair_odds_from_ai(ai_score: float, ai_rank: int) -> float:
    """AI指数から適正オッズを推定する（対数線形補間版）.

    アンカーポイント間をlog空間で線形補間し、滑らかなオッズカーブを生成。

    Args:
        ai_score: AI指数
        ai_rank: AI順位

    Returns:
        適正オッズの推定値
    """
    if ai_score <= 0:
        base_odds = {
            1: 3.0, 2: 5.0, 3: 8.0, 4: 12.0, 5: 18.0,
            6: 25.0, 7: 35.0, 8: 50.0, 9: 70.0, 10: 100.0,
        }
        return base_odds.get(ai_rank, 150.0)

    # スコアが最高アンカー以上
    if ai_score >= _AI_SCORE_ODDS_ANCHORS[0][0]:
        return _AI_SCORE_ODDS_ANCHORS[0][1]

    # 隣接アンカー間をlog空間で線形補間
    for i in range(len(_AI_SCORE_ODDS_ANCHORS) - 1):
        upper_score, upper_odds = _AI_SCORE_ODDS_ANCHORS[i]
        lower_score, lower_odds = _AI_SCORE_ODDS_ANCHORS[i + 1]

        if lower_score <= ai_score <= upper_score:
            # アンカー点で完全一致
            if ai_score == upper_score:
                return upper_odds
            if ai_score == lower_score:
                return lower_odds

            t = (ai_score - lower_score) / (upper_score - lower_score)
            log_upper = math.log(upper_odds)
            log_lower = math.log(lower_odds)
            return round(math.exp(log_lower + t * (log_upper - log_lower)), 2)

    return 50.0


def _estimate_fair_odds_fallback(popularity: int) -> float:
    """人気順位から適正オッズを推定する（フォールバック用）.

    注意: これは循環参照のため参考値としてのみ使用。
    正確な妙味分析にはAI指数が必要。

    Args:
        popularity: 人気順位

    Returns:
        適正オッズの推定値
    """
    fair_odds_by_pop = {
        1: 3.0, 2: 5.0, 3: 7.0, 4: 10.0, 5: 15.0,
        6: 20.0, 7: 30.0, 8: 40.0, 9: 50.0, 10: 70.0,
    }
    return fair_odds_by_pop.get(popularity, 100.0)


def _analyze_win_place_ratio(
    odds_history: list[dict],
    place_odds: list[dict],
    horse_numbers: list[int] | None,
) -> list[dict]:
    """単複比を分析する.

    単複比が高い馬 = 「頭は厳しいが複勝圏内」と市場が評価
    単複比が低い馬 = 「勝ち切り期待」と市場が評価

    Args:
        odds_history: 単勝オッズ履歴
        place_odds: 複勝オッズ
        horse_numbers: 分析対象馬番リスト

    Returns:
        単複比分析結果
    """
    if not odds_history or not place_odds:
        return []

    latest_win = odds_history[-1]
    win_odds_list = latest_win.get("odds", [])

    # 馬番でインデックス化
    win_odds_map = {o.get("horse_number"): o for o in win_odds_list}
    place_odds_map = {o.get("horse_number"): o for o in place_odds}

    results = []
    for horse_num, win_data in win_odds_map.items():
        if horse_numbers and horse_num not in horse_numbers:
            continue

        place_data = place_odds_map.get(horse_num)
        if not place_data:
            continue

        win_odds = win_data.get("odds", 0)
        # 複勝は範囲オッズの場合があるので中央値を使用
        place_min = place_data.get("odds_min", place_data.get("odds", 0))
        place_max = place_data.get("odds_max", place_data.get("odds", 0))

        if place_min and place_max:
            place_odds_avg = (place_min + place_max) / 2
        else:
            place_odds_avg = place_data.get("odds", 0)

        if win_odds <= 0 or place_odds_avg <= 0:
            continue

        ratio = win_odds / place_odds_avg

        # 判定
        if ratio >= WIN_PLACE_RATIO_HIGH:
            evaluation = "頭なし複勝向き"
            comment = "市場は複勝圏内は評価するが、勝ち切りは厳しいと判断"
            use_case = "ワイド・三連複の穴馬として"
        elif ratio <= WIN_PLACE_RATIO_LOW:
            evaluation = "勝ち切り期待"
            comment = "市場は勝ち切りを期待。軸向き"
            use_case = "単勝・馬連の軸として"
        else:
            evaluation = "標準"
            comment = "単複比は標準的"
            use_case = None

        # 特徴的な単複比のみ返却
        if evaluation != "標準":
            results.append({
                "horse_number": horse_num,
                "horse_name": win_data.get("horse_name", ""),
                "win_odds": win_odds,
                "place_odds": round(place_odds_avg, 1),
                "win_place_ratio": round(ratio, 1),
                "evaluation": evaluation,
                "comment": comment,
                "use_case": use_case,
            })

    # 単複比が高い順
    results.sort(key=lambda x: x.get("win_place_ratio", 0), reverse=True)
    return results[:5]


def _analyze_betting_patterns(
    movements: list[dict],
    time_based_analysis: dict,
) -> dict[str, list[int] | int | str | None]:
    """投票パターンを分析する."""
    pro_money_horses: list[int] = []
    public_favorite = None

    # 全体の急落馬
    for m in movements:
        if m.get("trend") in ("急落",) and m.get("alert_level") == "要注目":
            pro_money_horses.append(m.get("horse_number", 0))

    # 締切前の急変馬はより重要
    late_surge = time_based_analysis.get("late_surge_horses", [])
    late_surge_nums = [h.get("horse_number") for h in late_surge]

    # 重複を除いて統合
    pro_money_horses = list(set(pro_money_horses + late_surge_nums))

    # 最も人気を集めている馬
    if movements:
        lowest_odds_horse = min(movements, key=lambda x: x.get("current_odds", 999))
        public_favorite = lowest_odds_horse.get("horse_number", 0)

    # コメント生成
    if late_surge_nums:
        comment = f"{late_surge_nums}番に締切前の資金流入。関係者情報の可能性"
    elif pro_money_horses:
        comment = f"{pro_money_horses}番にプロの資金流入の兆候"
    else:
        comment = "特に目立った大口投票は検出されず"

    return {
        "pro_money_horses": pro_money_horses,
        "late_surge_horses": late_surge_nums,
        "public_favorite": public_favorite,
        "comment": comment,
    }


def _generate_odds_comment(
    movements: list[dict],
    time_based_analysis: dict,
    value_analysis: list[dict],
    win_place_ratio_analysis: list[dict],
    betting_patterns: dict,
) -> str:
    """総合コメントを生成する."""
    parts: list[str] = []

    # 締切前の急変（最重要）
    late_surge = time_based_analysis.get("late_surge_horses", [])
    if late_surge:
        horse = late_surge[0]
        parts.append(
            f"{horse.get('horse_number')}番が締切前に急変（{horse.get('change_rate')}%）。"
            "関係者筋の動きか要注目"
        )

    # オッズ急変馬
    if not late_surge:
        sharp_moves = [m for m in movements if m.get("trend") in ("急落", "急騰")]
        if sharp_moves:
            horse = sharp_moves[0]
            if horse.get("trend") == "急落":
                parts.append(
                    f"{horse.get('horse_number')}番のオッズ急落が目立つ"
                )
            else:
                parts.append(
                    f"{horse.get('horse_number')}番のオッズ急騰。人気離散の兆候"
                )

    # AI指数ベースの妙味馬
    value_horses = [v for v in value_analysis if v.get("value_rating") == "妙味あり"]
    if value_horses:
        horse = value_horses[0]
        if horse.get("ai_rank"):
            parts.append(
                f"{horse.get('horse_number')}番はAI{horse.get('ai_rank')}位でオッズ妙味あり"
            )
        else:
            parts.append(f"{horse.get('horse_number')}番は妙味あり。穴候補")

    # 単複比が特徴的な馬
    if win_place_ratio_analysis:
        high_ratio = [w for w in win_place_ratio_analysis if w.get("evaluation") == "頭なし複勝向き"]
        if high_ratio:
            horse = high_ratio[0]
            parts.append(
                f"{horse.get('horse_number')}番は単複比{horse.get('win_place_ratio')}。"
                "複勝向きと市場が評価"
            )

    if not parts:
        return "オッズに大きな変動なし。市場は安定"

    return "。".join(parts) + "。"
