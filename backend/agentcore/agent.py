"""馬券会議 AI エージェント.

AgentCore Runtime にデプロイされるメインエージェント。
"""

import json
import logging
import os
import re
import sys
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

# AgentCore Runtime ではCloudWatchメトリクス送信を有効化
os.environ.setdefault("EMIT_CLOUDWATCH_METRICS", "true")

# ツール承認をバイパス（自動化のため）
os.environ["BYPASS_TOOL_CONSENT"] = "true"

from bedrock_agentcore.runtime import BedrockAgentCoreApp

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
        "race_id": "...",  # レースID
        "user_id": "...",  # ユーザー識別子（"user:xxx" or "guest:xxx"）
    }
    """
    race_id = payload.get("race_id", "")
    user_id = payload.get("user_id", "")

    # DynamoDB から agent_data を取得し、好み設定をev_proposerツールに注入
    from tools.ev_proposer import set_betting_preference
    agent_data = _fetch_agent_data(user_id)
    betting_preference = agent_data.get("betting_preference") if agent_data else None
    set_betting_preference(betting_preference)

    # 入力バリデーション
    if not race_id:
        return {
            "message": "レースIDが必要です。",
            "session_id": getattr(context, "session_id", None),
            "suggested_questions": [],
        }

    # プロンプトを内部構築
    user_message = f"レースID {race_id} について買い目提案を生成してください。"

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


# DynamoDB リソース（コネクション再利用）
_dynamodb_resource = None
_AGENT_TABLE_NAME = os.environ.get("AGENT_TABLE_NAME", "baken-kaigi-agent")


def _fetch_agent_data(user_id: str) -> dict | None:
    """DynamoDB からエージェントデータを取得する.

    Args:
        user_id: ユーザー識別子（"user:xxx" or "guest:xxx"）

    Returns:
        エージェントデータの dict。見つからなければ None。
    """
    if not user_id or not user_id.startswith("user:"):
        return None

    # "user:xxx" -> "xxx"（Cognito sub）
    cognito_sub = user_id[5:]
    if not cognito_sub:
        return None

    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb")
    table = _dynamodb_resource.Table(_AGENT_TABLE_NAME)

    try:
        response = table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(cognito_sub),
        )
    except Exception:
        logger.exception("Failed to fetch agent data for user_id=%s", user_id)
        return None

    items = response.get("Items", [])
    if not items:
        return None

    return items[0]


if __name__ == "__main__":
    app.run()
