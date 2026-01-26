"""オッズ変動分析ツール.

オッズの変動パターンを分析し、市場の動向を読み解くツール。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# オッズ変動判定閾値
ODDS_SHARP_DROP = -30.0  # 30%以上下落: 急落
ODDS_DROP = -15.0  # 15%以上下落: 下落
ODDS_RISE = 15.0  # 15%以上上昇: 上昇
ODDS_SHARP_RISE = 30.0  # 30%以上上昇: 急騰

# 妙味判定閾値
VALUE_HIGH = 1.5  # 適正オッズの1.5倍以上: 妙味あり
VALUE_LOW = 0.7  # 適正オッズの0.7倍以下: 過剰人気


@tool
def analyze_odds_movement(
    race_id: str,
    horse_numbers: list[int] | None = None,
) -> dict:
    """オッズの変動パターンを分析する。

    オッズ変動トレンド、大口投票の検出、
    妙味のある馬の特定などを行います。

    Args:
        race_id: レースID
        horse_numbers: 特定馬のみ分析する場合は馬番リスト

    Returns:
        分析結果（市場概要、変動分析、妙味分析、投票パターンなど）
    """
    try:
        # オッズ履歴を取得
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/odds/history",
            params={"bet_type": "win"},
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "warning": "オッズデータが見つかりませんでした",
                "race_id": race_id,
            }

        response.raise_for_status()
        odds_data = response.json()

        odds_history = odds_data.get("odds_history", [])
        if not odds_history:
            return {
                "warning": "オッズ履歴がありません",
                "race_id": race_id,
            }

        # 市場概要
        market_overview = _analyze_market_overview(odds_history)

        # 馬ごとの変動分析
        movements = _analyze_movements(odds_history, horse_numbers)

        # 妙味分析
        value_analysis = _analyze_value(odds_history, horse_numbers)

        # 投票パターン分析
        betting_patterns = _analyze_betting_patterns(movements)

        # 総合コメント生成
        overall_comment = _generate_odds_comment(
            movements, value_analysis, betting_patterns
        )

        return {
            "race_id": race_id,
            "market_overview": market_overview,
            "movements": movements,
            "value_analysis": value_analysis,
            "betting_patterns": betting_patterns,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze odds movement: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze odds movement: {e}")
        return {"error": str(e)}


def _analyze_market_overview(odds_history: list[dict]) -> dict[str, dict | int | str | None]:
    """市場概要を分析する.

    Args:
        odds_history: オッズ履歴データ

    Returns:
        市場概要分析結果
    """
    if not odds_history:
        return {
            "favorite": None,
            "total_pool": 0,
            "market_confidence": "不明",
        }

    # 最新のオッズデータを取得
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
    odds_history: list[dict], horse_numbers: list[int] | None
) -> list[dict[str, str | int | float]]:
    """馬ごとのオッズ変動を分析する.

    Args:
        odds_history: オッズ履歴データ
        horse_numbers: 分析対象馬番リスト

    Returns:
        オッズ変動分析結果のリスト
    """
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
    return movements[:10]  # 上位10頭まで


def _analyze_value(
    odds_history: list[dict], horse_numbers: list[int] | None
) -> list[dict[str, str | int | float]]:
    """妙味分析を行う.

    Args:
        odds_history: オッズ履歴データ
        horse_numbers: 分析対象馬番リスト

    Returns:
        妙味分析結果のリスト
    """
    if not odds_history:
        return []

    latest = odds_history[-1]
    odds_list = latest.get("odds", [])

    value_horses = []
    for o in odds_list:
        horse_num = o.get("horse_number", 0)
        if horse_numbers and horse_num not in horse_numbers:
            continue

        curr_odds = o.get("odds", 0)
        if curr_odds <= 0:
            continue

        # 適正オッズ推定（簡易版: 順位から推定）
        # 実際には過去成績から算出すべき
        popularity = o.get("popularity", 10)
        estimated_fair_odds = _estimate_fair_odds(popularity)

        # 妙味判定
        if curr_odds <= 0 or estimated_fair_odds <= 0:
            continue

        value_ratio = curr_odds / estimated_fair_odds

        if value_ratio >= VALUE_HIGH:
            value_rating = "妙味あり"
            comment = "実力に対してオッズが高い。穴候補"
        elif value_ratio <= VALUE_LOW:
            value_rating = "過剰人気"
            comment = "人気先行。実力に対してオッズが低い"
        else:
            value_rating = "適正"
            comment = "オッズは実力相応"

        # 妙味ありのみ返却
        if value_rating == "妙味あり":
            value_horses.append({
                "horse_number": horse_num,
                "horse_name": o.get("horse_name", ""),
                "current_odds": curr_odds,
                "estimated_fair_odds": estimated_fair_odds,
                "value_rating": value_rating,
                "comment": comment,
            })

    return value_horses[:5]  # 上位5頭まで


def _estimate_fair_odds(popularity: int) -> float:
    """人気順位から適正オッズを推定する.

    Args:
        popularity: 人気順位

    Returns:
        適正オッズの推定値
    """
    # 簡易的な推定式
    fair_odds_by_pop = {
        1: 3.0,
        2: 5.0,
        3: 7.0,
        4: 10.0,
        5: 15.0,
        6: 20.0,
        7: 30.0,
        8: 40.0,
        9: 50.0,
        10: 70.0,
    }
    return fair_odds_by_pop.get(popularity, 100.0)


def _analyze_betting_patterns(movements: list[dict]) -> dict[str, list[int] | int | str | None]:
    """投票パターンを分析する.

    Args:
        movements: オッズ変動データ

    Returns:
        投票パターン分析結果
    """
    pro_money_horses: list[int] = []
    public_favorite = None

    for m in movements:
        if m.get("trend") in ("急落", "下落") and m.get("alert_level") == "要注目":
            pro_money_horses.append(m.get("horse_number", 0))

    # 最も人気を集めている馬（最もオッズが低い）
    if movements:
        lowest_odds_horse = min(movements, key=lambda x: x.get("current_odds", 999))
        public_favorite = lowest_odds_horse.get("horse_number", 0)

    # コメント生成
    if pro_money_horses:
        comment = f"{pro_money_horses}番にプロの資金流入の兆候"
    else:
        comment = "特に目立った大口投票は検出されず"

    return {
        "pro_money_horses": pro_money_horses,
        "public_favorite": public_favorite,
        "comment": comment,
    }


def _generate_odds_comment(
    movements: list[dict],
    value_analysis: list[dict],
    betting_patterns: dict,
) -> str:
    """総合コメントを生成する.

    Args:
        movements: オッズ変動データ
        value_analysis: 妙味分析結果
        betting_patterns: 投票パターン分析結果

    Returns:
        総合コメント
    """
    parts: list[str] = []

    # オッズ急変馬
    sharp_moves = [m for m in movements if m.get("trend") in ("急落", "急騰")]
    if sharp_moves:
        horse = sharp_moves[0]
        if horse.get("trend") == "急落":
            parts.append(
                f"{horse.get('horse_number')}番馬のオッズ急落が目立つ。関係者筋の動きか要注目"
            )
        else:
            parts.append(
                f"{horse.get('horse_number')}番馬のオッズ急騰。人気離散の兆候"
            )

    # 妙味馬
    if value_analysis:
        horse = value_analysis[0]
        parts.append(f"{horse.get('horse_number')}番は妙味あり。穴候補として注目")

    # プロ資金
    pro_horses = betting_patterns.get("pro_money_horses", [])
    if pro_horses:
        parts.append(f"{pro_horses}番にプロの資金流入の可能性")

    if not parts:
        return "オッズに大きな変動なし。市場は安定"

    return "。".join(parts) + "。"
