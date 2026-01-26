"""馬券会議 AI エージェント.

AgentCore Runtime にデプロイされるメインエージェント。
"""

import os

# ツール承認をバイパス（自動化のため）
os.environ["BYPASS_TOOL_CONSENT"] = "true"

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# 基本ツール
from tools.race_data import get_race_data
from tools.bet_analysis import analyze_bet_selection
from tools.pace_analysis import analyze_race_development, analyze_running_style_match
from tools.historical_analysis import (
    analyze_past_race_trends,
    analyze_jockey_course_stats,
    analyze_bet_roi,
)

# 馬・血統分析ツール
from tools.horse_analysis import analyze_horse_performance
from tools.training_analysis import analyze_training_condition
from tools.pedigree_analysis import analyze_pedigree_aptitude
from tools.course_aptitude_analysis import analyze_course_aptitude
from tools.weight_analysis import analyze_weight_trend
from tools.sire_analysis import analyze_sire_offspring

# 騎手・厩舎分析ツール
from tools.jockey_analysis import analyze_jockey_factor
from tools.trainer_analysis import analyze_trainer_tendency

# レース分析ツール
from tools.odds_analysis import analyze_odds_movement
from tools.gate_analysis import analyze_gate_position
from tools.rotation_analysis import analyze_rotation
from tools.race_comprehensive_analysis import analyze_race_comprehensive

# 馬券提案ツール
from tools.bet_combinations import suggest_bet_combinations

# Issue #102-111 追加ツール
from tools.bet_probability_analysis import analyze_bet_probability
from tools.track_condition_analysis import analyze_track_condition_impact
from tools.last_race_analysis import analyze_last_race_detail
from tools.class_analysis import analyze_class_factor
from tools.distance_change_analysis import analyze_distance_change
from tools.momentum_analysis import analyze_momentum
from tools.track_change_analysis import track_course_condition_change
from tools.scratch_impact_analysis import analyze_scratch_impact
from tools.time_analysis import analyze_time_performance

from prompts.consultation import SYSTEM_PROMPT

# Amazon Nova 2 Lite モデル（JP inference profile）
bedrock_model = BedrockModel(
    model_id=os.environ.get("BEDROCK_MODEL_ID", "jp.amazon.nova-2-lite-v1:0"),
    temperature=0.3,
)

# エージェント初期化（全29ツール登録）
agent = Agent(
    model=bedrock_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        # === 基本ツール（最初に使う） ===
        get_race_data,  # レース情報と出走馬を一括取得
        analyze_bet_selection,  # 買い目分析

        # === 展開・ペース分析 ===
        analyze_race_development,  # 展開予想
        analyze_running_style_match,  # 脚質適性

        # === 馬の分析 ===
        analyze_horse_performance,  # 過去成績分析
        analyze_training_condition,  # 調教状態分析
        analyze_pedigree_aptitude,  # 血統適性分析
        analyze_course_aptitude,  # コース適性分析
        analyze_weight_trend,  # 馬体重傾向分析
        analyze_sire_offspring,  # 種牡馬産駒分析

        # === 騎手・厩舎分析 ===
        analyze_jockey_factor,  # 騎手要因分析
        analyze_jockey_course_stats,  # 騎手コース成績
        analyze_trainer_tendency,  # 厩舎傾向分析

        # === レース分析 ===
        analyze_odds_movement,  # オッズ変動分析
        analyze_gate_position,  # 枠順分析
        analyze_rotation,  # ローテーション分析
        analyze_race_comprehensive,  # レース総合分析
        analyze_past_race_trends,  # 過去統計傾向

        # === 馬券・回収率分析 ===
        analyze_bet_roi,  # 回収率分析
        analyze_bet_probability,  # 的中率分析
        suggest_bet_combinations,  # 馬券組合せ提案

        # === 条件・環境分析 ===
        analyze_track_condition_impact,  # 馬場影響分析
        analyze_last_race_detail,  # 前走詳細分析
        analyze_class_factor,  # クラス要因分析
        analyze_distance_change,  # 距離変更影響分析
        analyze_momentum,  # 勢い・連勝分析
        track_course_condition_change,  # 馬場変化追跡
        analyze_scratch_impact,  # 出走取消影響分析
        analyze_time_performance,  # タイム分析
    ],
)

# AgentCore アプリ初期化
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context: dict) -> dict:
    """エージェント呼び出しハンドラー.

    payload 形式:
    {
        "prompt": "ユーザーメッセージ",
        "cart_items": [...],  # オプション: カート内容
        "session_id": "..."   # オプション: セッションID
    }
    """
    user_message = payload.get("prompt", "こんにちは")
    cart_items = payload.get("cart_items", [])

    # カート情報をコンテキストとして追加
    if cart_items:
        cart_summary = _format_cart_summary(cart_items)
        user_message = f"【現在のカート】\n{cart_summary}\n\n【質問】\n{user_message}"

    # エージェント実行
    result = agent(user_message)

    # レスポンスからテキストを抽出
    message_text = _extract_message_text(result.message)

    # クイックリプライ提案を抽出
    message_text, suggested_questions = _extract_suggested_questions(message_text)

    return {
        "message": message_text,
        "session_id": context.session_id,
        "suggested_questions": suggested_questions,
    }


def _extract_message_text(message) -> str:
    """Strands Agent のレスポンスからテキストを抽出する."""
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        # {"role": "assistant", "content": [{"text": "..."}]} 形式
        content = message.get("content", [])
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
            return "\n".join(texts)
        return str(content)
    return str(message)


def _extract_suggested_questions(text: str) -> tuple[str, list[str]]:
    """応答テキストからクイックリプライ提案を抽出する.

    Args:
        text: AIの応答テキスト

    Returns:
        (本文, 提案リスト) のタプル
    """
    separator = "---SUGGESTED_QUESTIONS---"

    if separator not in text:
        return text.strip(), []

    parts = text.split(separator, 1)
    main_text = parts[0].strip()

    if len(parts) < 2:
        return main_text, []

    questions_text = parts[1].strip()

    # すべての行を取得し、空行を除外
    raw_questions = [q.strip() for q in questions_text.split("\n") if q.strip()]

    # 先頭の「-」「- 」を除去（箇条書き形式の場合）
    questions = [q.lstrip("-").strip() for q in raw_questions]

    # 空の質問を除外し、5個までに制限
    questions = [q for q in questions if q][:5]

    return main_text, questions


def _format_cart_summary(cart_items: list) -> str:
    """カート内容をフォーマットする."""
    bet_type_names = {
        "win": "単勝",
        "place": "複勝",
        "quinella": "馬連",
        "quinella_place": "ワイド",
        "exacta": "馬単",
        "trio": "三連複",
        "trifecta": "三連単",
    }

    lines = []
    for item in cart_items:
        race_id = item.get("raceId", "")
        bet_type = item.get("betType", "")
        bet_type_display = bet_type_names.get(bet_type, bet_type)
        horse_numbers = item.get("horseNumbers", [])
        amount = item.get("amount", 0)
        race_name = item.get("raceName", "")

        line = f"- レースID:{race_id} {race_name} {bet_type_display} {horse_numbers} ¥{amount:,}"
        lines.append(line)

    return "\n".join(lines) if lines else "カートは空です"


if __name__ == "__main__":
    app.run()
