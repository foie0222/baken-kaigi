"""馬券会議 AI エージェント.

AgentCore Runtime にデプロイされるメインエージェント。
"""

import json
import logging
import os
import re
import sys
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

# AgentCore Runtime ではCloudWatchメトリクス送信を有効化
os.environ.setdefault("EMIT_CLOUDWATCH_METRICS", "true")

# ツール承認をバイパス（自動化のため）
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)
logger.info("Agent module loading started")

app = BedrockAgentCoreApp()
logger.info("BedrockAgentCoreApp created")

# エージェントは遅延初期化（初回呼び出し時に初期化）
# NOTE: AgentCore Runtime は各セッションを独立した microVM で実行するため、
# 並行リクエストによる競合状態（race condition）は発生しない。
# スレッドロックは不要。
_agent = None


def _create_agent(system_prompt: str, tools: list) -> Any:
    """指定されたシステムプロンプトとツールでエージェントを作成する."""
    from strands import Agent
    from strands.models import BedrockModel

    bedrock_model = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "jp.anthropic.claude-haiku-4-5-20251001-v1:0"),
        temperature=0.3,
    )
    logger.info(f"BedrockModel created with model_id: {bedrock_model.config.get('model_id')}")

    agent = Agent(
        model=bedrock_model,
        system_prompt=system_prompt,
        tools=tools,
    )
    logger.info(f"Agent created successfully with {len(tools)} tools")
    return agent


def _get_agent() -> Any:
    """エージェントを遅延初期化して取得する."""
    global _agent
    if _agent is None:
        logger.info("Lazy initializing agent...")
        from prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT
        from tool_router import get_tools
        _agent = _create_agent(BET_PROPOSAL_SYSTEM_PROMPT, tools=get_tools())
    return _agent


@app.entrypoint
def invoke(payload: dict, context: Any) -> dict:
    """エージェント呼び出しハンドラー.

    NOTE: context は bedrock_agentcore が提供する RequestContext (Pydantic) オブジェクト。
    dict ではないため getattr() でアクセスする。

    payload 形式:
    {
        "prompt": "ユーザーメッセージ",
        "runners_data": [...],  # オプション: 出走馬データ
        "session_id": "...",  # オプション: セッションID
        "agent_data": {  # オプション: エージェント育成データ
            "name": "エージェント名",
            "betting_preference": {...}
        }
    }
    """
    user_message = payload.get("prompt", "")
    runners_data = payload.get("runners_data", [])
    agent_data = payload.get("agent_data")

    # 好み設定をev_proposerツールに注入（preferred_bet_typesの解決に使用）
    from tools.ev_proposer import set_betting_preference
    betting_preference = agent_data.get("betting_preference") if agent_data else None
    set_betting_preference(betting_preference)

    # 入力バリデーション
    if not user_message:
        return {
            "message": "メッセージを入力してください。",
            "session_id": getattr(context, "session_id", None),
            "suggested_questions": [],
        }

    # 出走馬データをコンテキストとして追加
    if runners_data:
        runners_summary = _format_runners_summary(runners_data)
        user_message = f"【出走馬データ】\n{runners_summary}\n\n{user_message}"

    # エージェント実行
    agent = _get_agent()
    result = agent(user_message)

    # レスポンスからテキストを抽出
    message_text = _extract_message_text(result.message)

    # 買い目提案セパレータが欠落している場合、ツール結果から復元
    message_text = _ensure_bet_proposal_separator(message_text)

    # 買い目アクションを抽出（SUGGESTED_QUESTIONSより後に出力されるため先に抽出）
    message_text, bet_actions = _extract_bet_actions(message_text)

    # クイックリプライ提案を抽出
    message_text, suggested_questions = _extract_suggested_questions(message_text)

    return {
        "message": message_text,
        "session_id": getattr(context, "session_id", None),
        "suggested_questions": suggested_questions,
        "bet_actions": bet_actions,
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

    AIが ``---SUGGESTED_QUESTIONS---`` をマークダウン太字で出力する
    バリエーション（``**SUGGESTED_QUESTIONS---**`` 等）にも対応する。

    Args:
        text: AIの応答テキスト

    Returns:
        (本文, 提案リスト) のタプル
    """
    # 正規表現でセパレーターのバリエーションを検出（行全体がセパレーターである場合のみ）
    pattern = r"^\s*\*{0,2}-{0,3}\s*SUGGESTED_QUESTIONS\s*-{0,3}\*{0,2}\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)

    if not match:
        return text.strip(), []

    main_text = text[: match.start()].strip()
    questions_text = text[match.end() :].strip()

    if not questions_text:
        return main_text, []

    # すべての行を取得し、空行を除外
    raw_questions = [q.strip() for q in questions_text.split("\n") if q.strip()]

    # 1行に複数の質問が「？」区切りで並んでいる場合を展開
    expanded: list[str] = []
    for line in raw_questions:
        parts = re.split(r"？\s+", line)
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            if i < len(parts) - 1:
                part += "？"
            expanded.append(part)

    # 先頭の「-」「- 」を除去（箇条書き形式の場合）
    questions = [q.lstrip("-").strip() for q in expanded]

    # 空の質問を除外し、5個までに制限
    questions = [q for q in questions if q][:5]

    return main_text, questions


def _extract_bet_actions(text: str) -> tuple[str, list[dict]]:
    """応答テキストから買い目アクション情報を抽出する.

    Args:
        text: AIの応答テキスト

    Returns:
        (本文, アクションリスト) のタプル
    """
    from response_utils import BET_ACTIONS_SEPARATOR

    idx = text.find(BET_ACTIONS_SEPARATOR)
    if idx == -1:
        return text, []

    main_text = text[:idx].strip()
    json_text = text[idx + len(BET_ACTIONS_SEPARATOR) :].strip()

    if not json_text:
        return main_text, []

    try:
        actions = json.loads(json_text)
        if isinstance(actions, list):
            return main_text, actions[:5]
    except json.JSONDecodeError:
        # JSONパースに失敗した場合はアクションなしとして扱う
        pass

    return main_text, []


def _ensure_bet_proposal_separator(message_text: str) -> str:
    """買い目提案のセパレータが欠落している場合、ツール結果キャッシュから復元する."""
    from response_utils import BET_PROPOSALS_SEPARATOR, inject_bet_proposal_separator
    from tools.bet_proposal import get_last_proposal_result
    from tools.ev_proposer import get_last_ev_proposal_result

    # セパレータ有無に関わらず、呼び出し単位でツール結果キャッシュを必ず取得して消費する
    cached_result = get_last_proposal_result()
    cached_ev_result = get_last_ev_proposal_result()

    if BET_PROPOSALS_SEPARATOR in message_text:
        return message_text

    # EVプロポーザルのキャッシュを優先（新フロー）、なければ既存キャッシュ
    effective_result = cached_ev_result or cached_result
    if effective_result is not None:
        logger.info("BET_PROPOSALS_JSON separator missing, restoring from cached tool result")

    return inject_bet_proposal_separator(message_text, effective_result)


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
