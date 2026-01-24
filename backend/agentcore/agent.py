"""馬券会議 AI エージェント.

AgentCore Runtime にデプロイされるメインエージェント。
"""

import os

# ツール承認をバイパス（自動化のため）
os.environ["BYPASS_TOOL_CONSENT"] = "true"

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from tools.race_data import get_race_info, get_race_runners
from tools.bet_analysis import analyze_bet_selection
from tools.pace_analysis import analyze_race_development, analyze_running_style_match
from tools.historical_analysis import analyze_past_race_trends
from prompts.consultation import SYSTEM_PROMPT

# Amazon Nova 2 Lite モデル（コスト効率・高速・高精度）
# cross-region inference で東京リージョンからも利用可能
bedrock_model = BedrockModel(
    model_id=os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-2-lite-v1:0"),
    temperature=0.3,
)

# エージェント初期化
agent = Agent(
    model=bedrock_model,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        get_race_runners,
        get_race_info,
        analyze_bet_selection,
        analyze_race_development,
        analyze_running_style_match,
        analyze_past_race_trends,
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

    return {
        "message": message_text,
        "session_id": context.session_id,
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
