"""ローテーション分析ツール.

馬のローテーション（出走間隔・レース選択）を分析し、今回のレースへの適性を判断する。
"""

import logging
from datetime import datetime

from strands import tool

from . import dynamodb_client

logger = logging.getLogger(__name__)

# 定数定義
PERFORMANCE_LIMIT = 10

# 出走間隔の区分（日数）
SHORT_INTERVAL_MAX = 14  # 中2週以内
STANDARD_INTERVAL_MAX = 42  # 中6週以内
LONG_INTERVAL_MIN = 60  # 2ヶ月以上

# 間隔タイプの表示名
INTERVAL_LABELS = {
    0: "連闘",
    7: "中1週",
    14: "中2週",
    21: "中3週",
    28: "中4週",
    35: "中5週",
    42: "中6週",
}

# フィットネス評価
FITNESS_BASE = 70
FITNESS_MAX = 100
FITNESS_MIN = 30


@tool
def analyze_rotation(
    horse_id: str,
    horse_name: str,
    race_id: str,
) -> dict:
    """馬のローテーションを分析し、今回のレースへの適性を判断する。

    出走間隔の分析、ステップレースの適性判断、
    連闘・中1週の成績傾向、長期休養明けの影響を分析する。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        race_id: 対象レースID

    Returns:
        ローテーション分析結果（間隔情報、間隔別成績、ステップ分析、フィットネス推定）
    """
    try:
        # レース情報取得
        race_info = _get_race_info(race_id)
        if "error" in race_info:
            return race_info

        # 過去成績取得
        performances = _get_performances(horse_id)
        if not performances:
            return {
                "warning": "過去成績データが見つかりませんでした",
                "horse_name": horse_name,
            }

        # ローテーション情報
        rotation_info = _analyze_rotation_info(performances, race_info)

        # 間隔別成績
        interval_performance = _analyze_interval_performance(performances)

        # ステップレース分析
        step_analysis = _analyze_step_race(performances, race_info)

        # フィットネス推定
        fitness = _estimate_fitness(performances, rotation_info)

        # 総合コメント生成
        overall_comment = _generate_overall_comment(
            horse_name, rotation_info, interval_performance, step_analysis, fitness
        )

        return {
            "horse_name": horse_name,
            "rotation_info": rotation_info,
            "interval_performance": interval_performance,
            "step_race_analysis": step_analysis,
            "fitness_estimation": fitness,
            "overall_comment": overall_comment,
        }
    except Exception as e:
        logger.error(f"Failed to analyze rotation: {e}")
        return {"error": str(e)}


def _get_race_info(race_id: str) -> dict:
    """レース基本情報を取得する."""
    try:
        return dynamodb_client.get_race(race_id) or {}
    except Exception as e:
        logger.error(f"Failed to get race info: {e}")
        return {"error": f"レース情報取得エラー: {str(e)}"}


def _get_performances(horse_id: str) -> list[dict]:
    """過去成績を取得する."""
    try:
        return dynamodb_client.get_horse_performances(horse_id, limit=PERFORMANCE_LIMIT)
    except Exception as e:
        logger.error(f"Failed to get performances for horse {horse_id}: {e}")
        return []


def _analyze_rotation_info(performances: list[dict], race_info: dict) -> dict:
    """ローテーション情報を分析する."""
    if not performances:
        return {
            "days_since_last_race": None,
            "interval_type": "不明",
            "last_race": None,
            "rest_history": [],
        }

    # レース日付取得
    race_date_str = race_info.get("race_date", "")
    try:
        race_date = datetime.strptime(race_date_str, "%Y-%m-%d") if race_date_str else datetime.now()
    except ValueError:
        race_date = datetime.now()

    # 直近レース
    last_perf = performances[0]
    last_date_str = last_perf.get("race_date", "")
    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d") if last_date_str else None
    except ValueError:
        last_date = None

    # 出走間隔計算
    if last_date:
        days = (race_date - last_date).days
    else:
        days = None

    interval_type = _get_interval_label(days) if days is not None else "不明"

    last_race = {
        "date": last_date_str,
        "name": last_perf.get("race_name", ""),
        "result": f"{last_perf.get('finish_position', '')}着",
    }

    # 休養履歴
    rest_history = _calculate_rest_history(performances)

    return {
        "days_since_last_race": days,
        "interval_type": interval_type,
        "last_race": last_race,
        "rest_history": rest_history,
    }


def _get_interval_label(days: int | None) -> str:
    """日数から間隔ラベルを取得する."""
    if days is None or days < 0:
        return "不明"
    if days <= 7:
        return "連闘" if days <= 3 else "中1週"
    elif days <= 14:
        return "中2週"
    elif days <= 21:
        return "中3週"
    elif days <= 28:
        return "中4週"
    elif days <= 35:
        return "中5週"
    elif days <= 42:
        return "中6週"
    elif days <= 60:
        return "約2ヶ月"
    elif days <= 90:
        return "約3ヶ月"
    else:
        return f"{days // 30}ヶ月以上"


def _calculate_rest_history(performances: list[dict]) -> list[dict]:
    """過去の休養履歴を計算する."""
    history = []

    for i in range(len(performances) - 1):
        current = performances[i]
        previous = performances[i + 1]

        try:
            current_date = datetime.strptime(current.get("race_date", ""), "%Y-%m-%d")
            previous_date = datetime.strptime(previous.get("race_date", ""), "%Y-%m-%d")
            days = (current_date - previous_date).days
            interval = _get_interval_label(days)
        except (ValueError, TypeError):
            interval = "不明"

        finish = current.get("finish_position", 0)
        result = f"{finish}着" if finish else "不明"

        history.append({
            "interval": interval,
            "result": result,
        })

        if len(history) >= 5:
            break

    return history


def _analyze_interval_performance(performances: list[dict]) -> dict:
    """間隔別成績を分析する."""
    short_results = []  # 中2週以内
    standard_results = []  # 中3〜6週
    long_results = []  # 2ヶ月以上

    for i in range(len(performances) - 1):
        current = performances[i]
        previous = performances[i + 1]

        try:
            current_date = datetime.strptime(current.get("race_date", ""), "%Y-%m-%d")
            previous_date = datetime.strptime(previous.get("race_date", ""), "%Y-%m-%d")
            days = (current_date - previous_date).days
        except (ValueError, TypeError):
            continue

        finish = current.get("finish_position", 0)
        if finish <= 0:
            continue

        if days <= SHORT_INTERVAL_MAX:
            short_results.append(finish)
        elif days <= STANDARD_INTERVAL_MAX:
            standard_results.append(finish)
        elif days >= LONG_INTERVAL_MIN:
            long_results.append(finish)

    # 成績を集計
    short_record = _format_record(short_results)
    standard_record = _format_record(standard_results)
    long_record = _format_record(long_results)

    # ベスト間隔判定
    best_interval = _determine_best_interval(short_results, standard_results, long_results)

    # 現在の間隔評価
    current_rating = _rate_current_interval(performances, best_interval)

    # コメント生成
    comment = _generate_interval_comment(best_interval, short_results, standard_results, long_results)

    return {
        "short_interval_record": short_record,
        "standard_interval_record": standard_record,
        "long_interval_record": long_record,
        "best_interval": best_interval,
        "current_interval_rating": current_rating,
        "comment": comment,
    }


def _format_record(finishes: list[int]) -> str:
    """成績をフォーマットする."""
    if not finishes:
        return "0-0-0-0"

    win = sum(1 for f in finishes if f == 1)
    second = sum(1 for f in finishes if f == 2)
    third = sum(1 for f in finishes if f == 3)
    other = sum(1 for f in finishes if f > 3)

    return f"{win}-{second}-{third}-{other}"


def _determine_best_interval(
    short_results: list[int],
    standard_results: list[int],
    long_results: list[int],
) -> str:
    """ベストの出走間隔を判定する."""
    def avg_finish(results: list[int]) -> float:
        return sum(results) / len(results) if results else 10.0

    short_avg = avg_finish(short_results)
    standard_avg = avg_finish(standard_results)
    long_avg = avg_finish(long_results)

    best_avg = min(short_avg, standard_avg, long_avg)

    if best_avg == short_avg and short_results:
        return "中2週以内"
    elif best_avg == standard_avg and standard_results:
        return "中3〜4週"
    elif best_avg == long_avg and long_results:
        return "間隔空け"
    else:
        return "中3〜4週"  # デフォルト


def _rate_current_interval(performances: list[dict], best_interval: str) -> str:
    """現在の間隔を評価する."""
    if len(performances) < 2:
        return "B"

    try:
        current_date = datetime.strptime(performances[0].get("race_date", ""), "%Y-%m-%d")
        previous_date = datetime.strptime(performances[1].get("race_date", ""), "%Y-%m-%d")
        days = (current_date - previous_date).days
    except (ValueError, TypeError):
        return "B"

    # ベスト間隔との適合度で評価
    if best_interval == "中2週以内" and days <= SHORT_INTERVAL_MAX:
        return "A"
    elif best_interval == "中3〜4週" and 21 <= days <= 28:
        return "A"
    elif best_interval == "間隔空け" and days >= LONG_INTERVAL_MIN:
        return "A"
    elif days <= STANDARD_INTERVAL_MAX:
        return "B"
    else:
        return "C"


def _generate_interval_comment(
    best_interval: str,
    short_results: list[int],
    standard_results: list[int],
    long_results: list[int],
) -> str:
    """間隔別コメントを生成する."""
    parts = []

    if best_interval == "中2週以内":
        parts.append("詰めて使って良いタイプ")
    elif best_interval == "中3〜4週":
        parts.append("標準ローテが合う")
    else:
        parts.append("間隔空けて良化型")

    # 長期休養明けの傾向
    if long_results:
        long_avg = sum(long_results) / len(long_results)
        if long_avg >= 5:
            parts.append("休み明けは割引")
        elif long_avg <= 3:
            parts.append("休み明けも走る")

    return "。".join(parts)


def _analyze_step_race(performances: list[dict], race_info: dict) -> dict:
    """ステップレース分析を行う."""
    if not performances:
        return {
            "previous_race_class": "不明",
            "current_race_class": race_info.get("grade", "不明"),
            "step_type": "不明",
            "similar_pattern_record": "0-0-0-0",
            "rating": "不明",
            "comment": "データ不足",
        }

    last_perf = performances[0]
    previous_class = last_perf.get("grade_class", "不明")
    current_class = race_info.get("grade", "不明")

    # クラスの順序
    class_order = ["新馬", "未勝利", "1勝", "2勝", "3勝", "OP", "L", "G3", "G2", "G1"]

    prev_idx = class_order.index(previous_class) if previous_class in class_order else -1
    curr_idx = class_order.index(current_class) if current_class in class_order else -1

    # ステップタイプ判定
    if prev_idx < 0 or curr_idx < 0:
        step_type = "判定不可"
        rating = "不明"
    elif prev_idx > curr_idx:
        step_type = "格下げローテ"
        rating = "有利"
    elif prev_idx < curr_idx:
        step_type = "格上げローテ"
        rating = "厳しい"
    else:
        step_type = "同格ローテ"
        rating = "普通"

    # 類似パターンの成績
    similar_record = _find_similar_step_record(performances)

    # コメント
    comment = _generate_step_comment(step_type, previous_class, current_class, rating)

    return {
        "previous_race_class": previous_class,
        "current_race_class": current_class,
        "step_type": step_type,
        "similar_pattern_record": similar_record,
        "rating": rating,
        "comment": comment,
    }


def _find_similar_step_record(performances: list[dict]) -> str:
    """類似ステップパターンの成績を検索する."""
    # 簡易実装：直近5走の成績を返す
    finishes = [p.get("finish_position", 0) for p in performances[:5] if p.get("finish_position", 0) > 0]
    return _format_record(finishes)


def _generate_step_comment(
    step_type: str,
    previous_class: str,
    current_class: str,
    rating: str,
) -> str:
    """ステップコメントを生成する."""
    if rating == "有利":
        return f"{previous_class}から{current_class}への格下げは好材料"
    elif rating == "厳しい":
        return f"{previous_class}から{current_class}への格上げは壁がある"
    else:
        return f"{current_class}クラスでの同格対戦"


def _estimate_fitness(performances: list[dict], rotation_info: dict) -> dict:
    """フィットネスを推定する."""
    fitness = FITNESS_BASE

    days = rotation_info.get("days_since_last_race")

    # 間隔による調整
    if days is not None:
        if days <= 7:
            fitness -= 5  # 連闘は疲労懸念
        elif 21 <= days <= 35:
            fitness += 10  # 標準ローテは仕上がり良好
        elif days >= 90:
            fitness -= 15  # 長期休養明けは割引

    # 直近成績による調整
    if performances:
        recent_finishes = [p.get("finish_position", 0) for p in performances[:3] if p.get("finish_position", 0) > 0]
        if recent_finishes:
            avg = sum(recent_finishes) / len(recent_finishes)
            if avg <= 3:
                fitness += 10
            elif avg >= 6:
                fitness -= 10

    # 叩き回数
    history = rotation_info.get("rest_history", [])
    tataki_count = 0
    for h in history:
        if "週" in h.get("interval", ""):
            tataki_count += 1
        else:
            break

    if 1 <= tataki_count <= 2:
        fitness += 5  # 叩き2戦目は上昇

    fitness = min(FITNESS_MAX, max(FITNESS_MIN, fitness))

    # トレンド判定
    if fitness >= 85:
        trend = "上昇中"
    elif fitness >= 70:
        trend = "維持"
    else:
        trend = "要注意"

    # コメント
    comment = _generate_fitness_comment(fitness, days, tataki_count)

    return {
        "estimated_fitness": fitness,
        "fitness_trend": trend,
        "comment": comment,
    }


def _generate_fitness_comment(
    fitness: int,
    days: int | None,
    tataki_count: int,
) -> str:
    """フィットネスコメントを生成する."""
    parts = []

    if tataki_count == 1:
        parts.append("叩き2戦目で上昇気配")
    elif tataki_count >= 2:
        parts.append(f"叩き{tataki_count + 1}戦目")

    if days is not None and days >= 90:
        parts.append("休み明け初戦は割引")
    elif days is not None and days <= 7:
        parts.append("連闘で疲労残り懸念")

    if fitness >= 85:
        parts.append("仕上がり良好")
    elif fitness <= 50:
        parts.append("本調子ではない")

    return "。".join(parts) if parts else "普通の仕上がり"


def _generate_overall_comment(
    horse_name: str,
    rotation_info: dict,
    interval_performance: dict,
    step_analysis: dict,
    fitness: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    # 直近レースからの間隔
    last_race = rotation_info.get("last_race", {})
    interval = rotation_info.get("interval_type", "")
    if last_race is not None and interval:
        last_name = last_race.get("name", "前走")
        last_result = last_race.get("result", "")
        parts.append(f"{last_name}{last_result}から{interval}")

    # 間隔評価
    rating = interval_performance.get("current_interval_rating", "")
    if rating == "A":
        parts.append("理想的ローテ")
    elif rating == "C":
        parts.append("間隔に不安")

    # フィットネス
    fitness_val = fitness.get("estimated_fitness", 70)
    if fitness_val >= 85:
        parts.append("今回がピーク")
    elif fitness_val <= 50:
        parts.append("本調子ではない")

    return "。".join(parts) + "。"
