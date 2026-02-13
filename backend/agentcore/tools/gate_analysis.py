"""枠順分析ツール.

枠順・馬番の有利不利を分析するツール。
"""

import logging

from strands import tool

from . import dynamodb_client

logger = logging.getLogger(__name__)


@tool
def analyze_gate_position(
    race_id: str = "",
    horse_number: int = 0,
    horse_id: str = "",
    horse_name: str = "",
    running_style: str = "",
    venue: str = "",
    track_type: str = "",
    distance: int = 0,
) -> dict:
    """枠順・馬番の有利不利を分析する。

    コース別の枠順傾向、馬の枠順適性、脚質との相性、
    他馬との位置関係などを総合的に分析します。

    Args:
        race_id: レースID
        horse_number: 馬番
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        running_style: 脚質（逃げ/先行/差し/追込）
        venue: 競馬場名
        track_type: コース種別（芝/ダート）
        distance: レース距離

    Returns:
        分析結果（枠情報、コース傾向、馬の適性、脚質適合度など）
    """
    try:
        # 枠番計算（馬番から）
        gate = (horse_number - 1) // 2 + 1 if horse_number > 0 else 0
        position_type = _get_position_type(horse_number)

        # 枠情報
        gate_info = {
            "gate": gate,
            "horse_number": horse_number,
            "position_type": position_type,
        }

        # コース別枠順傾向を取得
        course_gate_tendency = _analyze_course_gate_tendency(
            venue, track_type, distance, gate
        )

        # 馬の枠順適性を取得
        horse_gate_aptitude = _analyze_horse_gate_aptitude(
            horse_id, position_type
        )

        # 脚質との相性
        running_style_fit = _analyze_running_style_fit(
            running_style, position_type
        )

        # フィールド分析（簡易版）
        field_analysis = _analyze_field(position_type, running_style)

        # 総合コメント生成
        overall_comment = _generate_gate_comment(
            horse_name,
            gate,
            horse_number,
            position_type,
            course_gate_tendency,
            horse_gate_aptitude,
            running_style,
        )

        return {
            "horse_name": horse_name,
            "gate_info": gate_info,
            "course_gate_tendency": course_gate_tendency,
            "horse_gate_aptitude": horse_gate_aptitude,
            "running_style_fit": running_style_fit,
            "field_analysis": field_analysis,
            "overall_comment": overall_comment,
        }
    except Exception as e:
        logger.error(f"Failed to analyze gate position: {e}")
        return {"error": str(e)}


def _get_position_type(horse_number: int) -> str:
    """馬番から位置タイプを判定する.

    Args:
        horse_number: 馬番

    Returns:
        位置タイプ（内枠/中枠/外枠/不明）
    """
    if horse_number <= 0:
        return "不明"
    elif horse_number <= 6:
        return "内枠"
    elif horse_number <= 12:
        return "中枠"
    else:
        return "外枠"


def _analyze_course_gate_tendency(
    venue: str, track_type: str, distance: int, gate: int
) -> dict[str, str | int | float | list[int]]:
    """コース別の枠順傾向を分析する.

    Args:
        venue: 競馬場名
        track_type: コース種別
        distance: 距離
        gate: 枠番

    Returns:
        コース別枠順傾向分析結果
    """
    # DynamoDBに対応テーブルなし（将来HRDB-API経由で取得予定）
    logger.info("gate statistics data not available in DynamoDB, returning empty")
    gate_stats = []

    # データ取得失敗時のデフォルト
    return {
        "venue": venue,
        "track_type": track_type,
        "distance": distance,
        "favorable_gates": [],
        "unfavorable_gates": [],
        "current_gate_win_rate": 10.0,
        "avg_win_rate": 10.0,
        "rating": "普通",
        "comment": "枠順傾向データなし",
    }


def _analyze_horse_gate_aptitude(horse_id: str, position_type: str) -> dict[str, str]:
    """馬の枠順適性を分析する.

    Args:
        horse_id: 馬コード
        position_type: 位置タイプ

    Returns:
        馬の枠順適性分析結果
    """
    if not horse_id:
        return {
            "inner_gate_record": "データなし",
            "middle_gate_record": "データなし",
            "outer_gate_record": "データなし",
            "best_position": "不明",
            "current_position_rating": "C",
            "comment": "馬情報がないため分析不可",
        }

    # DynamoDBに対応テーブルなし（将来HRDB-API経由で取得予定）
    logger.info("course aptitude data not available in DynamoDB, returning empty")

    return {
        "inner_gate_record": "データなし",
        "middle_gate_record": "データなし",
        "outer_gate_record": "データなし",
        "best_position": "不明",
        "current_position_rating": "C",
        "comment": "枠順適性データ取得失敗",
    }


def _analyze_running_style_fit(running_style: str, position_type: str) -> dict[str, str]:
    """脚質と枠順の相性を分析する.

    Args:
        running_style: 脚質
        position_type: 位置タイプ

    Returns:
        脚質と枠順の相性分析結果
    """
    # 脚質×枠の一般的な相性
    fit_matrix = {
        "逃げ": {"内枠": "好相性", "中枠": "普通", "外枠": "やや不利"},
        "先行": {"内枠": "好相性", "中枠": "好相性", "外枠": "やや不利"},
        "差し": {"内枠": "普通", "中枠": "好相性", "外枠": "好相性"},
        "追込": {"内枠": "やや不利", "中枠": "普通", "外枠": "好相性"},
    }

    style_fit = fit_matrix.get(running_style, {}).get(position_type, "普通")

    # コメント生成
    if running_style in ("逃げ", "先行"):
        if position_type == "内枠":
            comment = f"{running_style}馬にとって内目の枠は有利。スムーズに好位取れる"
        elif position_type == "外枠":
            comment = f"{running_style}馬だが外枠。ポジション取りに注意が必要"
        else:
            comment = f"{running_style}馬。中枠からでも十分"
    else:  # 差し・追込
        if position_type == "外枠":
            comment = f"{running_style}馬にとって外枠は悪くない。直線で外を回せる"
        elif position_type == "内枠":
            comment = f"{running_style}馬だが内枠。包まれるリスクに注意"
        else:
            comment = f"{running_style}馬。中枠から適度な位置取りが可能"

    return {
        "running_style": running_style,
        "style_gate_fit": style_fit,
        "comment": comment,
    }


def _analyze_field(position_type: str, running_style: str) -> dict[str, str | list[str]]:
    """フィールド分析（簡易版）.

    Args:
        position_type: 位置タイプ
        running_style: 脚質

    Returns:
        フィールド分析結果
    """
    # 実際にはレース出走馬情報を取得して分析すべき
    # ここでは簡易的なデフォルト値を返す
    return {
        "inside_horses": [],
        "potential_pace": "普通",
        "position_advantage": f"{position_type}から{'好位' if running_style in ('逃げ', '先行') else '中団'}取りの展開",
        "comment": "出走馬データから詳細分析が必要",
    }


def _generate_gate_comment(
    horse_name: str,
    gate: int,
    horse_number: int,
    position_type: str,
    course_tendency: dict,
    horse_aptitude: dict,
    running_style: str,
) -> str:
    """総合コメントを生成する.

    Args:
        horse_name: 馬名
        gate: 枠番
        horse_number: 馬番
        position_type: 位置タイプ
        course_tendency: コース傾向
        horse_aptitude: 馬の適性
        running_style: 脚質

    Returns:
        総合コメント
    """
    parts: list[str] = []

    # 枠番評価
    course_rating = course_tendency.get("rating", "普通")
    if course_rating in ("有利", "やや有利"):
        parts.append(f"{gate}枠{horse_number}番は好枠")
    elif course_rating == "不利":
        parts.append(f"{gate}枠{horse_number}番はやや厳しい枠")
    else:
        parts.append(f"{gate}枠{horse_number}番は普通の枠")

    # 馬の適性
    horse_rating = horse_aptitude.get("current_position_rating", "C")
    best_pos = horse_aptitude.get("best_position", "")
    if horse_rating in ("A", "B") and best_pos == position_type:
        parts.append(f"{position_type}は得意パターン")

    # 脚質との相性
    if running_style in ("逃げ", "先行") and position_type == "内枠":
        parts.append("先行策が取りやすい")
    elif running_style in ("差し", "追込") and position_type == "外枠":
        parts.append("直線で外を回せる")

    if not parts:
        return f"{horse_name}の枠順に特筆事項なし。"

    return "。".join(parts) + "。"
