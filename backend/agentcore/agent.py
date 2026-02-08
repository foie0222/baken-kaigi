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
        from tools.bet_proposal import generate_bet_proposal
        from tools.odds_analysis import analyze_odds_movement
        from tools.pace_analysis import analyze_race_characteristics
        from tools.past_performance import get_past_performance
        from tools.race_data import get_race_runners
        from tools.risk_analysis import analyze_risk_factors
        from tools.speed_index import get_speed_index, list_speed_indices_for_date

        bedrock_model = BedrockModel(
            model_id=os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0"),
            temperature=0.3,
        )
        logger.info(f"BedrockModel created with model_id: {bedrock_model.config.get('model_id')}")

        _agent = Agent(
            model=bedrock_model,
            system_prompt=SYSTEM_PROMPT,
            tools=[
                get_ai_prediction,  # AI指数取得（ai-shisu.com）
                get_speed_index,  # スピード指数取得
                list_speed_indices_for_date,  # 日付別スピード指数一覧
                get_past_performance,  # 馬柱（過去成績）取得
                get_race_runners,  # レース出走馬データ取得（JRA-VAN API）
                analyze_bet_selection,  # JRA統計ベース買い目分析
                analyze_odds_movement,  # オッズ変動・妙味分析
                analyze_race_characteristics,  # 展開予想・レース特性分析
                analyze_risk_factors,  # リスク分析・心理バイアス対策
                generate_bet_proposal,  # 買い目提案一括生成
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
        "runners_data": [...],  # オプション: 出走馬データ
        "session_id": "..."   # オプション: セッションID
    }
    """
    user_message = payload.get("prompt", "")
    cart_items = payload.get("cart_items", [])
    runners_data = payload.get("runners_data", [])

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

    # 出走馬データをコンテキストとして追加
    if runners_data:
        runners_summary = _format_runners_summary(runners_data)
        user_message = f"【出走馬データ】\n{runners_summary}\n\n{user_message}"

    # エージェント実行（遅延初期化）
    agent = _get_agent()
    result = agent(user_message)

    # レスポンスからテキストを抽出
    message_text = _extract_message_text(result.message)

    # 買い目提案セパレータが欠落している場合、ツール結果から復元
    message_text = _ensure_bet_proposal_separator(message_text)

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


def _ensure_bet_proposal_separator(message_text: str) -> str:
    """買い目提案のセパレータが欠落している場合、ツール結果キャッシュから復元する."""
    from response_utils import BET_PROPOSALS_SEPARATOR, inject_bet_proposal_separator
    from tools.bet_proposal import get_last_proposal_result

    # セパレータ有無に関わらず、呼び出し単位でツール結果キャッシュを必ず取得して消費する
    cached_result = get_last_proposal_result()

    if BET_PROPOSALS_SEPARATOR in message_text:
        return message_text

    if cached_result is not None:
        logger.info("BET_PROPOSALS_JSON separator missing, restoring from cached tool result")

    return inject_bet_proposal_separator(message_text, cached_result)


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


def _format_runners_summary(runners_data: list) -> str:
    """出走馬データをフォーマットする."""
    lines = []
    for runner in runners_data:
        number = runner.get("horse_number", "?")
        name = runner.get("horse_name", "不明")
        odds = runner.get("odds")
        popularity = runner.get("popularity")
        frame = runner.get("frame_number")
        if frame is None:
            frame = runner.get("waku_ban")

        parts = [f"{number}番 {name}"]
        if odds is not None:
            parts.append(f"オッズ:{odds}")
        if popularity is not None:
            parts.append(f"{popularity}番人気")
        if frame is not None:
            parts.append(f"{frame}枠")

        lines.append("- " + " ".join(parts))

    return "\n".join(lines) if lines else "出走馬データなし"


if __name__ == "__main__":
    app.run()
