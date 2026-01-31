"""馬券会議 AI エージェント.

AgentCore Runtime にデプロイされるメインエージェント。
"""

import os

# ツール承認をバイパス（自動化のため）
os.environ["BYPASS_TOOL_CONSENT"] = "true"

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# AI予想データ（コールドスタート軽減のためツールを絞り込み）
from tools.ai_prediction import get_ai_prediction, list_ai_predictions_for_date

from prompts.consultation import SYSTEM_PROMPT

# Amazon Nova 2 Lite モデル（JP inference profile）
bedrock_model = BedrockModel(
    model_id=os.environ.get("BEDROCK_MODEL_ID", "jp.amazon.nova-2-lite-v1:0"),
    temperature=0.3,
)

# エージェント初期化（コールドスタート軽減のためツールを2つに絞り込み）
agent = Agent(
    model=bedrock_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        # === 外部AI予想 ===
        get_ai_prediction,  # AI指数取得（ai-shisu.com）
        list_ai_predictions_for_date,  # 日別AI予想一覧
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
