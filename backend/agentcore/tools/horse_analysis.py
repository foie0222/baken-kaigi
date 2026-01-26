"""馬の分析ツール.

馬の過去成績、調教、血統、厩舎などを分析するツール群。
"""

import logging
from typing import Any

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30
DEFAULT_PERFORMANCE_LIMIT = 5
MAX_PERFORMANCE_LIMIT = 20

# 調子評価の閾値
GOOD_FORM_AVG_FINISH = 3.0  # 平均着順がこれ以下なら好調
POOR_FORM_AVG_FINISH = 6.0  # 平均着順がこれ以上なら不調

# 上がり3F能力評価の閾値（秒）
FINISHING_SPEED_A_THRESHOLD = 33.5
FINISHING_SPEED_B_THRESHOLD = 34.0
FINISHING_SPEED_C_THRESHOLD = 34.5

# 着順安定性評価の閾値（標準偏差）
CONSISTENCY_HIGH_THRESHOLD = 2.0
CONSISTENCY_LOW_THRESHOLD = 4.0


@tool
def analyze_horse_performance(
    horse_id: str,
    horse_name: str,
    limit: int = 5,
) -> dict:
    """馬の過去成績を分析し、傾向や能力を判断する。

    直近の成績からフォーム、末脚能力、安定性、
    クラス適性、距離適性を総合的に分析します。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        limit: 分析対象レース数（デフォルト5、最大20）

    Returns:
        分析結果（フォーム評価、能力分析、距離適性、コメント）
    """
    try:
        # limit のバリデーション
        limit = min(max(1, limit), MAX_PERFORMANCE_LIMIT)

        response = requests.get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": limit},
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "warning": "過去成績データが見つかりませんでした",
                "horse_name": horse_name,
            }

        response.raise_for_status()
        data = response.json()

        performances = data.get("performances", [])
        if not performances:
            return {
                "warning": "過去成績がありません",
                "horse_name": horse_name,
            }

        # 直近N走の着順リスト
        recent_finishes = [p.get("finish_position", 0) for p in performances]
        recent_form = "-".join(str(f) for f in recent_finishes)

        # フォーム評価（調子判定）
        form_rating = _evaluate_form(recent_finishes)

        # 能力分析
        ability_analysis = _analyze_ability(performances)

        # クラス分析
        class_analysis = _analyze_class(performances)

        # 距離適性分析
        distance_preference = _analyze_distance(performances)

        # コメント生成
        comment = _generate_performance_comment(
            horse_name, recent_finishes, form_rating, ability_analysis
        )

        return {
            "horse_name": horse_name,
            "recent_form": recent_form,
            "form_rating": form_rating,
            "ability_analysis": ability_analysis,
            "class_analysis": class_analysis,
            "distance_preference": distance_preference,
            "comment": comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze horse performance: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze horse performance: {e}")
        return {"error": str(e)}


def _evaluate_form(finishes: list[int]) -> str:
    """調子を評価する."""
    if not finishes:
        return "データなし"

    # 馬券圏内（3着以内）の回数
    in_money = sum(1 for f in finishes if 1 <= f <= 3)
    in_money_rate = in_money / len(finishes)

    # 平均着順
    valid_finishes = [f for f in finishes if f > 0]
    avg_finish = sum(valid_finishes) / len(valid_finishes) if valid_finishes else 10

    # 直近3走の傾向（改善傾向かどうか）
    if len(finishes) >= 3:
        recent_3 = finishes[:3]
        improving = recent_3[0] < recent_3[-1]  # 直近が良くなっている
    else:
        improving = False

    if in_money_rate >= 0.6 and avg_finish <= GOOD_FORM_AVG_FINISH:
        return "好調"
    elif in_money_rate >= 0.4 or avg_finish <= POOR_FORM_AVG_FINISH:
        if improving:
            return "上昇中"
        return "普通"
    else:
        return "不調"


def _analyze_ability(performances: list[dict]) -> dict:
    """能力を分析する."""
    # 上がり3F分析
    last_3f_times = []
    for p in performances:
        last_3f = p.get("last_3f")
        if last_3f and isinstance(last_3f, (int, float)) and last_3f > 0:
            last_3f_times.append(last_3f)

    if last_3f_times:
        avg_last_3f = sum(last_3f_times) / len(last_3f_times)
        if avg_last_3f <= FINISHING_SPEED_A_THRESHOLD:
            finishing_speed = "A"
        elif avg_last_3f <= FINISHING_SPEED_B_THRESHOLD:
            finishing_speed = "B"
        elif avg_last_3f <= FINISHING_SPEED_C_THRESHOLD:
            finishing_speed = "C"
        else:
            finishing_speed = "D"
    else:
        finishing_speed = "データなし"

    # 着順の安定性（標準偏差）
    finishes = [p.get("finish_position", 0) for p in performances if p.get("finish_position", 0) > 0]
    if len(finishes) >= 2:
        mean = sum(finishes) / len(finishes)
        variance = sum((f - mean) ** 2 for f in finishes) / len(finishes)
        std_dev = variance ** 0.5
        if std_dev <= CONSISTENCY_HIGH_THRESHOLD:
            consistency = "高い"
        elif std_dev <= CONSISTENCY_LOW_THRESHOLD:
            consistency = "普通"
        else:
            consistency = "低い"
    else:
        consistency = "データ不足"

    # スタミナ評価（長距離での成績）
    long_distance_perfs = [p for p in performances if p.get("distance", 0) >= 2000]
    if long_distance_perfs:
        long_avg = sum(p.get("finish_position", 10) for p in long_distance_perfs) / len(long_distance_perfs)
        if long_avg <= 3:
            stamina = "A"
        elif long_avg <= 5:
            stamina = "B"
        else:
            stamina = "C"
    else:
        stamina = "データなし"

    return {
        "finishing_speed": finishing_speed,
        "stamina": stamina,
        "consistency": consistency,
    }


def _analyze_class(performances: list[dict]) -> dict:
    """クラス適性を分析する."""
    # クラス分布を集計
    class_results: dict[str, list[int]] = {}
    for p in performances:
        grade_class = p.get("grade_class", "不明")
        finish = p.get("finish_position", 0)
        if finish > 0:
            if grade_class not in class_results:
                class_results[grade_class] = []
            class_results[grade_class].append(finish)

    # 最頻出クラス（現在のクラス）
    current_class = max(class_results.keys(), key=lambda k: len(class_results[k])) if class_results else "不明"

    # クラス適性判定
    class_order = ["新馬", "未勝利", "1勝", "2勝", "3勝", "OP", "L", "G3", "G2", "G1"]

    suitable_classes = []
    for cls, finishes in class_results.items():
        avg = sum(finishes) / len(finishes)
        if avg <= 5:  # 平均5着以内なら適性あり
            suitable_classes.append(cls)

    # クラス上昇余地の判定
    current_idx = class_order.index(current_class) if current_class in class_order else -1
    class_up_potential = False
    if current_idx >= 0 and current_idx < len(class_order) - 1:
        current_finishes = class_results.get(current_class, [])
        if current_finishes:
            avg = sum(current_finishes) / len(current_finishes)
            if avg <= 2.5:  # 現クラスで平均2.5着以内なら上昇余地あり
                class_up_potential = True

    return {
        "current_class": current_class,
        "suitable_class": "〜".join(sorted(suitable_classes, key=lambda x: class_order.index(x) if x in class_order else 99)[:2]) if suitable_classes else current_class,
        "class_up_potential": class_up_potential,
    }


def _analyze_distance(performances: list[dict]) -> dict:
    """距離適性を分析する."""
    # 距離カテゴリ別の成績
    short_perfs = [p for p in performances if p.get("distance", 0) < 1600]
    middle_perfs = [p for p in performances if 1600 <= p.get("distance", 0) < 2000]
    long_perfs = [p for p in performances if p.get("distance", 0) >= 2000]

    def avg_finish(perfs: list[dict]) -> float | None:
        finishes = [p.get("finish_position", 0) for p in perfs if p.get("finish_position", 0) > 0]
        return sum(finishes) / len(finishes) if finishes else None

    short_avg = avg_finish(short_perfs)
    middle_avg = avg_finish(middle_perfs)
    long_avg = avg_finish(long_perfs)

    def performance_rating(avg: float | None) -> str:
        if avg is None:
            return "データなし"
        elif avg <= 3:
            return "得意"
        elif avg <= 5:
            return "普通"
        else:
            return "苦手"

    # ベスト距離の判定
    distances = [p.get("distance", 0) for p in performances if p.get("distance", 0) > 0]
    if distances:
        min_dist = min(distances)
        max_dist = max(distances)
        best_range = f"{min_dist}-{max_dist}m"
    else:
        best_range = "データなし"

    return {
        "best_range": best_range,
        "short_performance": performance_rating(short_avg),
        "middle_performance": performance_rating(middle_avg),
        "long_performance": performance_rating(long_avg),
    }


def _generate_performance_comment(
    horse_name: str,
    finishes: list[int],
    form_rating: str,
    ability: dict,
) -> str:
    """成績分析のコメントを生成する."""
    # 馬券圏内回数
    in_money = sum(1 for f in finishes if 1 <= f <= 3)

    base = f"直近{len(finishes)}走で馬券圏内{in_money}回"

    if form_rating == "好調":
        form_comment = "と安定した成績"
    elif form_rating == "上昇中":
        form_comment = "で上昇気配"
    elif form_rating == "不調":
        form_comment = "とやや低迷中"
    else:
        form_comment = ""

    # 末脚評価
    speed = ability.get("finishing_speed", "")
    if speed == "A":
        speed_comment = "。上がり3Fは毎回33秒台で末脚は確実"
    elif speed == "B":
        speed_comment = "。末脚はまずまず"
    else:
        speed_comment = ""

    return f"{base}{form_comment}{speed_comment}。"
