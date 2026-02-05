"""馬券会議 AI エージェント.

AgentCore Runtime にデプロイされるメインエージェント。
"""

import logging
import os
import sys
from typing import Any

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)
logger.info("Agent module loading started")

# ツール承認をバイパス（自動化のため）
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 最小限のインポートのみモジュールレベルで実行（30秒以内に完了必須）
from bedrock_agentcore.runtime import BedrockAgentCoreApp

logger.info("BedrockAgentCoreApp imported")

# AgentCore アプリ初期化（軽量なので即座に実行）
app = BedrockAgentCoreApp()
logger.info("BedrockAgentCoreApp created")

# エージェントは遅延初期化（初回呼び出し時に初期化）
# NOTE: AgentCore Runtime は各セッションを独立した microVM で実行するため、
# 並行リクエストによる競合状態（race condition）は発生しない。
# スレッドロックは不要。
_agent = None


def _get_agent():
    """エージェントを遅延初期化して取得する."""
    global _agent
    if _agent is None:
        logger.info("Lazy initializing agent...")

        from prompts.consultation import SYSTEM_PROMPT
        from strands import Agent
        from strands.models import BedrockModel
        from tools.ai_prediction import get_ai_prediction
        from tools.bet_analysis import analyze_bet_selection
        from tools.odds_analysis import analyze_odds_movement
        from tools.pace_analysis import analyze_race_characteristics

        bedrock_model = BedrockModel(
            model_id=os.environ.get("BEDROCK_MODEL_ID", "jp.amazon.nova-2-lite-v1:0"),
            temperature=0.3,
        )
        logger.info(f"BedrockModel created with model_id: {bedrock_model.config.get('model_id')}")

        _agent = Agent(
            model=bedrock_model,
            system_prompt=SYSTEM_PROMPT,
            tools=[
                get_ai_prediction,  # AI指数取得（ai-shisu.com）
                analyze_bet_selection,  # JRA統計ベース買い目分析
                analyze_odds_movement,  # オッズ変動・妙味分析
                analyze_race_characteristics,  # 展開予想・レース特性分析
            ],
        )
        logger.info("Agent created successfully")
    return _agent


@app.entrypoint
def invoke(payload: dict, context: Any) -> dict:
    """エージェント呼び出しハンドラー.

    NOTE: context は bedrock_agentcore が提供する RequestContext (Pydantic) オブジェクト。
    dict ではないため getattr() でアクセスする。

    payload 形式:
    {
        "prompt": "ユーザーメッセージ",
        "cart_items": [...],  # オプション: カート内容
        "session_id": "..."   # オプション: セッションID
    }
    """
    user_message = payload.get("prompt", "")
    cart_items = payload.get("cart_items", [])

    # 入力バリデーション
    if not user_message and not cart_items:
        return {
            "message": "カートに買い目を追加してからご相談ください。",
            "session_id": getattr(context, "session_id", None),
            "suggested_questions": [],
        }

    # promptが空でもcart_itemsがあれば分析を開始
    if not user_message and cart_items:
        user_message = "カートの買い目についてAI指数と照らし合わせて分析し、リスクや弱点を指摘してください。"

    # カート情報をコンテキストとして追加
    if cart_items:
        cart_summary = _format_cart_summary(cart_items)
        user_message = f"【現在のカート】\n{cart_summary}\n\n【質問】\n{user_message}"

    # エージェント実行（遅延初期化）
    agent = _get_agent()
    result = agent(user_message)

    # レスポンスからテキストを抽出
    message_text = _extract_message_text(result.message)

    # クイックリプライ提案を抽出
    message_text, suggested_questions = _extract_suggested_questions(message_text)

    return {
        "message": message_text,
        "session_id": getattr(context, "session_id", None),
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
