"""調教分析ツール.

調教データを分析し、レースへの仕上がり具合を判断するツール。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30
DEFAULT_TRAINING_LIMIT = 5
DEFAULT_DAYS = 30

# 調教評価基準（栗東CW 5F基準）
KURITTO_CW_5F_EXCELLENT = 51.0  # 51秒以下: 超優秀
KURITTO_CW_5F_GOOD = 53.0  # 53秒以下: 良好
KURITTO_CW_5F_AVERAGE = 55.0  # 55秒以下: 普通

# 美浦W 5F基準
MIHO_W_5F_EXCELLENT = 52.0
MIHO_W_5F_GOOD = 54.0
MIHO_W_5F_AVERAGE = 56.0

# 坂路基準（栗東坂路 4F）
SLOPE_4F_EXCELLENT = 51.0
SLOPE_4F_GOOD = 53.0
SLOPE_4F_AVERAGE = 55.0

# 上がり3F評価基準
LAST_3F_EXCELLENT = 12.0  # 12秒以下: 超優秀
LAST_3F_GOOD = 12.5  # 12.5秒以下: 良好
LAST_3F_AVERAGE = 13.0  # 13秒以下: 普通


@tool
def analyze_training_condition(
    horse_id: str,
    horse_name: str,
    race_id: str = "",
) -> dict:
    """馬の調教データを分析し、仕上がり具合を判断する。

    直近の調教から状態、トレーナーの意図、過去パターンとの
    比較などを総合的に分析します。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        race_id: 対象レース（省略時は最新の調教を分析）

    Returns:
        分析結果（調教サマリー、状態評価、勝負気配など）
    """
    try:
        response = requests.get(
            f"{get_api_url()}/horses/{horse_id}/training",
            params={"limit": DEFAULT_TRAINING_LIMIT, "days": DEFAULT_DAYS},
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "warning": "調教データが見つかりませんでした",
                "horse_name": horse_name,
            }

        response.raise_for_status()
        data = response.json()

        training_records = data.get("training_records", [])
        training_summary = data.get("training_summary", {})

        if not training_records:
            return {
                "warning": "調教データがありません",
                "horse_name": horse_name,
            }

        # 直近の調教を分析
        last_workout = _analyze_last_workout(training_records[0])

        # 全体傾向を分析
        trend_analysis = _analyze_trend(training_records, training_summary)

        # 状態評価
        condition_rating = _evaluate_condition(
            training_records, last_workout, trend_analysis
        )

        # トレーナーの意図を推測
        trainer_intent = _analyze_trainer_intent(training_records)

        # 過去パターンとの比較
        historical_pattern = _analyze_historical_pattern(training_records)

        # 総合コメント生成
        overall_comment = _generate_comment(
            horse_name, last_workout, condition_rating, trainer_intent
        )

        return {
            "horse_name": horse_name,
            "training_summary": {
                "last_workout": last_workout,
                "comparison_to_previous": trend_analysis.get("comparison"),
                "trend": trend_analysis.get("trend"),
            },
            "condition_rating": condition_rating,
            "trainer_intent": trainer_intent,
            "historical_pattern": historical_pattern,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze training condition: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze training condition: {e}")
        return {"error": str(e)}


def _analyze_last_workout(record: dict) -> dict[str, str]:
    """直近の調教を分析する.

    Args:
        record: 調教レコード

    Returns:
        調教分析結果（日付、コース、タイム、評価等）
    """
    course = record.get("course", "")
    time_str = record.get("time", "")
    last_3f = record.get("last_3f")

    # タイム評価
    evaluation = _evaluate_time(course, time_str, last_3f)

    return {
        "date": record.get("date", ""),
        "course": course,
        "time": time_str,
        "last_3f": str(last_3f) if last_3f else "",
        "evaluation": evaluation,
        "training_type": record.get("training_type", ""),
        "comment": record.get("comment", ""),
    }


def _evaluate_time(course: str, time_str: str, last_3f: float | None) -> str:
    """調教タイムを評価する.

    Args:
        course: 調教コース名
        time_str: タイム文字列
        last_3f: 上がり3Fタイム（将来の拡張用）

    Returns:
        評価（A/B/C/D/評価不能）
    """
    if not time_str:
        return "評価不能"

    try:
        # タイムを秒に変換（例: "52.3" -> 52.3）
        time_sec = float(time_str)
    except (ValueError, TypeError):
        return "評価不能"

    # コース別の基準で評価
    if "CW" in course or "W" in course:
        # ウッドチップコース
        if "栗東" in course:
            if time_sec <= KURITTO_CW_5F_EXCELLENT:
                return "A"
            elif time_sec <= KURITTO_CW_5F_GOOD:
                return "B"
            elif time_sec <= KURITTO_CW_5F_AVERAGE:
                return "C"
            else:
                return "D"
        else:
            # 美浦
            if time_sec <= MIHO_W_5F_EXCELLENT:
                return "A"
            elif time_sec <= MIHO_W_5F_GOOD:
                return "B"
            elif time_sec <= MIHO_W_5F_AVERAGE:
                return "C"
            else:
                return "D"
    elif "坂" in course:
        # 坂路
        if time_sec <= SLOPE_4F_EXCELLENT:
            return "A"
        elif time_sec <= SLOPE_4F_GOOD:
            return "B"
        elif time_sec <= SLOPE_4F_AVERAGE:
            return "C"
        else:
            return "D"
    else:
        # その他のコース（基準なし）
        return "B"


def _analyze_trend(records: list[dict], summary: dict) -> dict[str, str]:
    """調教の傾向を分析する.

    Args:
        records: 調教レコードのリスト
        summary: 調教サマリー

    Returns:
        傾向分析結果（比較、傾向）
    """
    if len(records) < 2:
        return {
            "comparison": "比較データなし",
            "trend": "判定不能",
        }

    # 直近と前回のタイム比較
    try:
        latest_time = float(records[0].get("time", "0") or "0")
        previous_time = float(records[1].get("time", "0") or "0")

        if latest_time > 0 and previous_time > 0:
            diff = latest_time - previous_time
            if diff < -0.5:
                comparison = "タイム短縮"
                trend = "上昇傾向"
            elif diff > 0.5:
                comparison = "タイム低下"
                trend = "下降傾向"
            else:
                comparison = "タイム安定"
                trend = "維持"
        else:
            comparison = "比較データなし"
            trend = "判定不能"
    except (ValueError, TypeError):
        comparison = "比較データなし"
        trend = "判定不能"

    # サマリーから傾向を補完
    if summary and summary.get("recent_trend"):
        trend = summary.get("recent_trend")

    return {
        "comparison": comparison,
        "trend": trend,
    }


def _evaluate_condition(
    records: list[dict], last_workout: dict, trend_analysis: dict
) -> str:
    """状態を評価する.

    Args:
        records: 調教レコードのリスト
        last_workout: 直近調教の分析結果
        trend_analysis: 傾向分析結果

    Returns:
        状態評価（絶好調/好調/普通/不安）
    """
    score = 0

    # 直近調教の評価から加点
    eval_scores = {"A": 3, "B": 2, "C": 1, "D": 0}
    last_eval = last_workout.get("evaluation", "")
    score += eval_scores.get(last_eval, 0)

    # 傾向から加点
    trend = trend_analysis.get("trend", "")
    if trend == "上昇傾向":
        score += 2
    elif trend == "維持":
        score += 1
    elif trend == "下降傾向":
        score -= 1

    # 調教本数から加点（多ければ仕上げに力を入れている）
    if len(records) >= 4:
        score += 1
    elif len(records) <= 1:
        score -= 1

    # スコアから状態判定
    if score >= 5:
        return "絶好調"
    elif score >= 3:
        return "好調"
    elif score >= 1:
        return "普通"
    else:
        return "不安"


def _analyze_trainer_intent(records: list[dict]) -> dict[str, str | bool]:
    """トレーナーの意図を分析する.

    Args:
        records: 調教レコードのリスト

    Returns:
        トレーナー意図分析結果（強度、勝負レースか、コメント）
    """
    # 調教強度を判定
    workout_count = len(records)
    has_strong_workout = any(
        r.get("evaluation") in ("A", "優", "特優") for r in records
    )

    if workout_count >= 4 and has_strong_workout:
        intensity = "強め"
        is_target = True
        comment = "追い切り本数多く、勝負気配濃厚"
    elif workout_count >= 3:
        intensity = "普通"
        is_target = False
        comment = "標準的な仕上げ"
    else:
        intensity = "軽め"
        is_target = False
        comment = "調整程度の調教"

    return {
        "workout_intensity": intensity,
        "is_target_race": is_target,
        "comment": comment,
    }


def _analyze_historical_pattern(records: list[dict]) -> dict[str, str]:
    """過去パターンとの比較を行う.

    Args:
        records: 調教レコードのリスト

    Returns:
        過去パターン分析結果
    """
    # 現時点では簡易的な分析
    # 将来的にはDBから過去の同様パターンを検索して比較
    good_workouts = sum(
        1 for r in records if r.get("evaluation") in ("A", "B", "優", "特優", "良")
    )
    total = len(records)

    if total == 0:
        return {
            "similar_prep_results": "データなし",
            "comment": "過去データ不足",
        }

    good_rate = good_workouts / total
    if good_rate >= 0.6:
        return {
            "similar_prep_results": f"好走率{int(good_rate * 100)}%",
            "comment": f"直近{total}本中{good_workouts}本が好調教",
        }
    else:
        return {
            "similar_prep_results": f"好走率{int(good_rate * 100)}%",
            "comment": "調教内容にやや物足りなさ",
        }


def _generate_comment(
    horse_name: str,
    last_workout: dict,
    condition_rating: str,
    trainer_intent: dict,
) -> str:
    """総合コメントを生成する.

    Args:
        horse_name: 馬名
        last_workout: 直近調教の分析結果
        condition_rating: 状態評価
        trainer_intent: トレーナー意図分析結果

    Returns:
        総合コメント
    """
    course = last_workout.get("course", "")
    time_str = last_workout.get("time", "")
    evaluation = last_workout.get("evaluation", "")

    parts = []

    # 調教タイム情報
    if course and time_str:
        parts.append(f"{course}{time_str}秒")

    # 評価コメント
    if evaluation == "A":
        parts.append("自己ベスト級の動き")
    elif evaluation == "B":
        parts.append("まずまずの動き")
    elif evaluation == "C":
        parts.append("平凡な動き")
    elif evaluation == "D":
        parts.append("物足りない動き")

    # 状態評価
    condition_comments = {
        "絶好調": "仕上がり万全で狙い目",
        "好調": "好仕上がり",
        "普通": "まずまずの仕上がり",
        "不安": "仕上がりに不安あり",
    }
    parts.append(condition_comments.get(condition_rating, ""))

    # 勝負気配
    if trainer_intent.get("is_target_race"):
        parts.append("勝負気配濃厚")

    return "。".join(p for p in parts if p) + "。"
