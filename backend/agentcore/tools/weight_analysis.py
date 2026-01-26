"""馬体重分析ツール.

馬体重の推移を分析し、レースへの影響を判断するツール。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# 馬体重変動判定閾値
WEIGHT_BIG_CHANGE = 10  # 10kg以上は大幅変動
WEIGHT_MODERATE_CHANGE = 6  # 6kg以上はやや大きい変動


@tool
def analyze_weight_trend(
    horse_id: str,
    horse_name: str,
    current_weight: int | None = None,
    current_weight_diff: int | None = None,
) -> dict:
    """馬体重の推移を分析する。

    馬体重の推移トレンド、増減と成績の相関、
    ベスト体重、当日馬体重の評価などを行います。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        current_weight: 当日馬体重（発表後に指定）
        current_weight_diff: 前走比増減

    Returns:
        分析結果（体重履歴、トレンド分析、ベスト体重、当日評価など）
    """
    try:
        # 過去成績を取得（体重データ含む）
        response = requests.get(
            f"{get_api_url()}/horses/{horse_id}/performances",
            params={"limit": 10},
            headers=get_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return {
                "warning": "馬体重データが見つかりませんでした",
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

        # 体重履歴を抽出
        weight_history = _extract_weight_history(performances)

        # トレンド分析
        trend_analysis = _analyze_trend(weight_history)

        # ベスト体重推定
        optimal_weight = _estimate_optimal_weight(weight_history)

        # 体重変動と成績の相関
        weight_performance_correlation = _analyze_weight_performance_correlation(
            weight_history
        )

        # 当日馬体重評価
        current_weight_evaluation = _evaluate_current_weight(
            current_weight, current_weight_diff, optimal_weight, weight_history
        )

        # 総合コメント生成
        overall_comment = _generate_weight_comment(
            horse_name,
            current_weight_evaluation,
            trend_analysis,
            optimal_weight,
        )

        return {
            "horse_name": horse_name,
            "weight_history": weight_history[:5],  # 直近5走
            "trend_analysis": trend_analysis,
            "optimal_weight": optimal_weight,
            "weight_performance_correlation": weight_performance_correlation,
            "current_weight_evaluation": current_weight_evaluation,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze weight trend: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze weight trend: {e}")
        return {"error": str(e)}


def _extract_weight_history(performances: list[dict]) -> list[dict]:
    """成績データから体重履歴を抽出する."""
    history = []
    for p in performances:
        weight = p.get("horse_weight")
        if weight and weight > 0:
            # 前走との差分計算
            diff_str = ""
            if len(history) > 0:
                prev_weight = history[-1].get("weight", 0)
                if prev_weight > 0:
                    diff = weight - prev_weight
                    diff_str = f"+{diff}" if diff >= 0 else str(diff)

            history.append({
                "date": p.get("race_date", ""),
                "weight": weight,
                "diff": diff_str,
                "result": f"{p.get('finish_position', 0)}着",
                "race_name": p.get("race_name", ""),
                "finish_position": p.get("finish_position", 0),
            })

    return history


def _analyze_trend(weight_history: list[dict]) -> dict:
    """馬体重のトレンドを分析する."""
    if not weight_history:
        return {
            "trend": "データなし",
            "avg_weight": 0,
            "weight_range": "不明",
            "stability": "不明",
        }

    weights = [w.get("weight", 0) for w in weight_history if w.get("weight", 0) > 0]

    if not weights:
        return {
            "trend": "データなし",
            "avg_weight": 0,
            "weight_range": "不明",
            "stability": "不明",
        }

    avg_weight = sum(weights) / len(weights)
    min_weight = min(weights)
    max_weight = max(weights)
    weight_range = f"{min_weight}-{max_weight}"

    # トレンド判定（直近と過去の比較）
    if len(weights) >= 3:
        recent_avg = sum(weights[:2]) / 2
        older_avg = sum(weights[2:]) / len(weights[2:])
        diff = recent_avg - older_avg

        if diff >= 4:
            trend = "増加傾向"
        elif diff <= -4:
            trend = "減少傾向"
        else:
            trend = "安定"
    else:
        trend = "データ不足"

    # 安定性（標準偏差）
    if len(weights) >= 2:
        variance = sum((w - avg_weight) ** 2 for w in weights) / len(weights)
        std_dev = variance ** 0.5
        if std_dev <= 3:
            stability = "非常に安定"
        elif std_dev <= 5:
            stability = "安定"
        else:
            stability = "変動大きい"
    else:
        stability = "データ不足"

    return {
        "trend": trend,
        "avg_weight": int(avg_weight),
        "weight_range": weight_range,
        "stability": stability,
    }


def _estimate_optimal_weight(weight_history: list[dict]) -> dict:
    """ベスト体重を推定する."""
    if not weight_history:
        return {
            "estimated_best": 0,
            "best_range": "不明",
            "comment": "データ不足",
        }

    # 好走時（3着以内）の体重を抽出
    good_weights = [
        w.get("weight", 0)
        for w in weight_history
        if w.get("finish_position", 99) <= 3 and w.get("weight", 0) > 0
    ]

    if good_weights:
        avg_good = sum(good_weights) / len(good_weights)
        estimated_best = int(avg_good)
        best_range = f"{estimated_best - 4}-{estimated_best + 4}"
        comment = f"{estimated_best}kg前後で好走が多い"
    else:
        # 好走データがない場合は全体平均
        all_weights = [w.get("weight", 0) for w in weight_history if w.get("weight", 0) > 0]
        if all_weights:
            avg_all = sum(all_weights) / len(all_weights)
            estimated_best = int(avg_all)
            best_range = f"{estimated_best - 4}-{estimated_best + 4}"
            comment = "好走時のデータ不足。平均体重から推定"
        else:
            estimated_best = 0
            best_range = "不明"
            comment = "データ不足"

    return {
        "estimated_best": estimated_best,
        "best_range": best_range,
        "comment": comment,
    }


def _analyze_weight_performance_correlation(weight_history: list[dict]) -> dict:
    """体重変動と成績の相関を分析する."""
    # 増加時と減少時の成績を比較
    increase_results = []
    decrease_results = []

    for i, w in enumerate(weight_history):
        diff_str = w.get("diff", "")
        finish = w.get("finish_position", 99)

        if diff_str.startswith("+"):
            try:
                diff = int(diff_str[1:])
                if diff > 0:
                    increase_results.append({"diff": diff, "finish": finish})
            except ValueError:
                pass
        elif diff_str.startswith("-"):
            try:
                diff = abs(int(diff_str))
                decrease_results.append({"diff": diff, "finish": finish})
            except ValueError:
                pass

    # 増加時の評価
    if increase_results:
        avg_finish_inc = sum(r["finish"] for r in increase_results) / len(increase_results)
        if avg_finish_inc <= 3:
            increase_performance = "良い"
        elif avg_finish_inc <= 5:
            increase_performance = "やや良い"
        else:
            increase_performance = "普通"
    else:
        increase_performance = "データなし"

    # 減少時の評価
    if decrease_results:
        avg_finish_dec = sum(r["finish"] for r in decrease_results) / len(decrease_results)
        if avg_finish_dec <= 3:
            decrease_performance = "良い"
        elif avg_finish_dec <= 5:
            decrease_performance = "やや良い"
        else:
            decrease_performance = "普通"
    else:
        decrease_performance = "データなし"

    # コメント生成
    if increase_performance in ("良い", "やや良い") and decrease_performance not in ("良い", "やや良い"):
        comment = "増加時に好走傾向"
    elif decrease_performance in ("良い", "やや良い") and increase_performance not in ("良い", "やや良い"):
        comment = "減少時に好走傾向"
    else:
        comment = "体重増減と成績の明確な相関なし"

    return {
        "increase_performance": increase_performance,
        "decrease_performance": decrease_performance,
        "big_change_threshold": WEIGHT_BIG_CHANGE,
        "comment": comment,
    }


def _evaluate_current_weight(
    current_weight: int | None,
    current_weight_diff: int | None,
    optimal_weight: dict,
    weight_history: list[dict],
) -> dict:
    """当日馬体重を評価する."""
    if not current_weight:
        return {
            "weight": None,
            "diff": None,
            "rating": "未発表",
            "vs_optimal": "",
            "comment": "当日馬体重は未発表",
        }

    diff_str = ""
    if current_weight_diff is not None:
        diff_str = f"+{current_weight_diff}" if current_weight_diff >= 0 else str(current_weight_diff)

    # ベスト体重との比較
    estimated_best = optimal_weight.get("estimated_best", 0)
    best_range = optimal_weight.get("best_range", "")

    if estimated_best > 0:
        diff_from_best = abs(current_weight - estimated_best)
        if diff_from_best <= 4:
            vs_optimal = "ベスト体重の範囲内"
            rating_base = "良好"
        elif diff_from_best <= 8:
            vs_optimal = "ベスト体重からやや外れる"
            rating_base = "普通"
        else:
            vs_optimal = "ベスト体重から大きく外れる"
            rating_base = "不安"
    else:
        vs_optimal = "比較データなし"
        rating_base = "普通"

    # 増減幅による調整
    if current_weight_diff is not None:
        abs_diff = abs(current_weight_diff)
        if abs_diff >= WEIGHT_BIG_CHANGE:
            rating = "要注意"
            comment = f"前走から{diff_str}kgは大幅変動。状態面に注意"
        elif abs_diff >= WEIGHT_MODERATE_CHANGE:
            rating = "やや注意"
            comment = f"前走から{diff_str}kgはやや大きい変動"
        else:
            rating = rating_base
            comment = f"前走から{diff_str}kgは許容範囲"
    else:
        rating = rating_base
        comment = "増減不明"

    return {
        "weight": current_weight,
        "diff": diff_str,
        "rating": rating,
        "vs_optimal": vs_optimal,
        "comment": comment,
    }


def _generate_weight_comment(
    horse_name: str,
    current_weight_evaluation: dict,
    trend_analysis: dict,
    optimal_weight: dict,
) -> str:
    """総合コメントを生成する."""
    parts = []

    weight = current_weight_evaluation.get("weight")
    diff = current_weight_evaluation.get("diff", "")
    rating = current_weight_evaluation.get("rating", "")
    vs_optimal = current_weight_evaluation.get("vs_optimal", "")

    if weight:
        parts.append(f"馬体重{weight}kg（{diff}）")

        if vs_optimal:
            parts.append(vs_optimal)

        trend = trend_analysis.get("trend", "")
        if trend == "増加傾向":
            parts.append("成長中の証か")
        elif trend == "減少傾向":
            parts.append("絞れてきた印象")

        if rating in ("良好",):
            parts.append("状態良さそう")
        elif rating in ("要注意",):
            parts.append("状態面に注意が必要")
    else:
        estimated = optimal_weight.get("estimated_best", 0)
        if estimated:
            parts.append(f"ベスト体重は{estimated}kg前後と推定")

    if not parts:
        return f"{horse_name}の馬体重データは不足"

    return "。".join(parts) + "。"
