"""レース分析ツール.

レースデータを収集し、各馬のAI予想生データと分析情報を提供する。
LLMが各ソースのスコア・順位を直接見て買い目判断する。
"""

import logging

from strands import tool

logger = logging.getLogger(__name__)


@tool
def analyze_race_for_betting(race_id: str) -> dict:
    """レースを分析し、各馬のAI予想生データと分析情報を返す。

    AI指数（各ソースのスコア・順位）、脚質、スピード指数を取得し、
    LLMが各ソースの生データを直接見て勝率を判断する。

    Args:
        race_id: レースID (例: "202602010511")

    Returns:
        dict: レース分析結果
            - race_info: レース基本情報（難易度、脚質構成、見送りスコア、コンセンサス等）
            - horses: 各馬の情報（AI予想、脚質、スピード指数）
    """
    try:
        from .ai_prediction import get_ai_prediction
        from .pace_analysis import _get_running_styles
        from .race_data import _extract_race_conditions, _fetch_race_detail
        from .speed_index import get_speed_index

        # レースデータ取得
        race_detail = _fetch_race_detail(race_id)
        race = race_detail.get("race", {})
        runners_data = race_detail.get("runners", [])
        race_conditions = _extract_race_conditions(race)

        # AI予想取得
        ai_result = get_ai_prediction(race_id)
        if not isinstance(ai_result, dict) or "error" in ai_result:
            return {"error": f"AI予想の取得に失敗: {ai_result}"}

        # 脚質データ取得
        running_styles = _get_running_styles(race_id)

        # スピード指数取得
        speed_index_data = None
        si_result = get_speed_index(race_id)
        if isinstance(si_result, dict) and "error" not in si_result:
            speed_index_data = si_result

        return _analyze_race_impl(
            race_id=race_id,
            race_name=race.get("race_name", ""),
            venue=race.get("venue", ""),
            distance=race.get("distance", ""),
            surface=race.get("track_type", ""),
            total_runners=race.get("horse_count", len(runners_data)),
            race_conditions=race_conditions,
            runners_data=runners_data,
            ai_result=ai_result,
            running_styles=running_styles,
            speed_index_data=speed_index_data,
        )
    except Exception as e:
        logger.exception("analyze_race_for_betting failed")
        return {"error": f"レース分析に失敗しました: {e}"}


def _analyze_race_impl(
    race_id: str,
    race_name: str,
    venue: str,
    distance: str,
    surface: str,
    total_runners: int,
    race_conditions: list[str],
    runners_data: list[dict],
    ai_result: dict,
    running_styles: list[dict] | None = None,
    speed_index_data: dict | None = None,
) -> dict:
    """レース分析の実装（テスト用に公開）.

    Args:
        race_id: レースID
        race_name: レース名
        venue: 競馬場名
        distance: 距離
        surface: 馬場
        total_runners: 出走頭数
        race_conditions: レース条件リスト
        runners_data: 出走馬データ
        ai_result: AI予想結果 (sources配列, consensus)
        running_styles: 脚質データ
        speed_index_data: スピード指数データ

    Returns:
        レース分析結果 (race_info, horses)
    """
    from .bet_proposal import _assess_ai_consensus, _calculate_confidence_factor
    from .pace_analysis import _assess_race_difficulty
    from .risk_analysis import _assess_skip_recommendation

    running_styles = running_styles or []

    # 脚質構成サマリー
    running_style_summary: dict[str, int] = {}
    for rs in running_styles:
        style = rs.get("running_style", "不明")
        running_style_summary[style] = running_style_summary.get(style, 0) + 1

    # レース難易度
    difficulty = _assess_race_difficulty(total_runners, race_conditions, venue, runners_data)

    # 見送りスコア
    ai_predictions = []
    sources = ai_result.get("sources", [])
    if sources:
        ai_predictions = sources[0].get("predictions", [])
    skip = _assess_skip_recommendation(
        total_runners,
        race_conditions,
        venue,
        runners_data,
        ai_predictions,
    )
    skip_score = skip.get("skip_score", 0)
    confidence_factor = _calculate_confidence_factor(skip_score)

    # AI合議
    ai_consensus = _assess_ai_consensus(ai_predictions) if ai_predictions else "データなし"

    # 脚質マップ
    style_map = {rs.get("horse_number"): rs.get("running_style", "") for rs in running_styles}

    # スピード指数マップ（全ソースの指数を馬番ごとに集約）
    si_map: dict[int, dict] = {}
    if speed_index_data and "sources" in speed_index_data:
        for source_data in speed_index_data["sources"]:
            source_name = source_data.get("source", "")
            for idx_entry in source_data.get("indices", []):
                hn = idx_entry.get("horse_number")
                value = idx_entry.get("value")
                if hn is not None and value is not None:
                    hn = int(hn)
                    if hn not in si_map:
                        si_map[hn] = {}
                    si_map[hn][source_name] = float(value)

    # AI予想マップ（全ソース: スコア+順位）
    ai_predictions_map: dict[int, dict] = {}
    for source in sources:
        source_name = source.get("source", "")
        for pred in source.get("predictions", []):
            hn = int(pred.get("horse_number", 0))
            score = float(pred.get("score", 0))
            rank = int(pred.get("rank", 0))
            if hn > 0:
                if hn not in ai_predictions_map:
                    ai_predictions_map[hn] = {}
                ai_predictions_map[hn][source_name] = {"score": score, "rank": rank}

    # 各馬の情報を構築
    horses = []
    for runner in runners_data:
        hn = int(runner.get("horse_number", 0))
        style = style_map.get(hn, "")

        horses.append(
            {
                "number": hn,
                "name": runner.get("horse_name", ""),
                "odds": float(runner.get("odds", 0)),
                "ai_predictions": ai_predictions_map.get(hn, {}),
                "running_style": style or None,
                "speed_index": si_map.get(hn),
            }
        )

    return {
        "race_info": {
            "race_id": race_id,
            "race_name": race_name,
            "venue": venue,
            "distance": distance,
            "surface": surface,
            "total_runners": total_runners,
            "difficulty": difficulty,
            "running_style_summary": running_style_summary,
            "skip_score": skip_score,
            "ai_consensus": ai_consensus,
            "confidence_factor": confidence_factor,
            "consensus": ai_result.get("consensus"),
        },
        "horses": horses,
    }
