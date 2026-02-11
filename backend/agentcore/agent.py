"""馬券会議 AI エージェント.

AgentCore Runtime にデプロイされるメインエージェント。
"""

import logging
import os
import re
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
_consultation_agent = None
_bet_proposal_agent = None


def _create_agent(system_prompt: str) -> Any:
    """指定されたシステムプロンプトでエージェントを作成する."""
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
        model_id=os.environ.get("BEDROCK_MODEL_ID", "jp.anthropic.claude-haiku-4-5-20251001-v1:0"),
        temperature=0.3,
    )
    logger.info(f"BedrockModel created with model_id: {bedrock_model.config.get('model_id')}")

    agent = Agent(
        model=bedrock_model,
        system_prompt=system_prompt,
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
    return agent


def _get_agent(request_type: str | None = None) -> Any:
    """エージェントを遅延初期化して取得する."""
    global _consultation_agent, _bet_proposal_agent

    if request_type == "bet_proposal":
        if _bet_proposal_agent is None:
            logger.info("Lazy initializing bet_proposal agent...")
            from prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT
            _bet_proposal_agent = _create_agent(BET_PROPOSAL_SYSTEM_PROMPT)
        return _bet_proposal_agent

    if _consultation_agent is None:
        logger.info("Lazy initializing consultation agent...")
        from prompts.consultation import SYSTEM_PROMPT
        _consultation_agent = _create_agent(SYSTEM_PROMPT)
    return _consultation_agent


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
        "session_id": "...",  # オプション: セッションID
        "type": "bet_proposal"  # オプション: "bet_proposal" で買い目提案専用プロンプトを使用
    }
    """
    user_message = payload.get("prompt", "")
    cart_items = payload.get("cart_items", [])
    runners_data = payload.get("runners_data", [])
    request_type = payload.get("type")

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
    agent = _get_agent(request_type)
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

    AIが ``---SUGGESTED_QUESTIONS---`` をマークダウン太字で出力する
    バリエーション（``**SUGGESTED_QUESTIONS---**`` 等）にも対応する。

    Args:
        text: AIの応答テキスト

    Returns:
        (本文, 提案リスト) のタプル
    """
    # 正規表現でセパレーターのバリエーションを検出
    pattern = r"\*{0,2}-{0,3}\s*SUGGESTED_QUESTIONS\s*-{0,3}\*{0,2}"
    match = re.search(pattern, text)

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
    """カート内容をフォーマットする.

    各買い目を明確に表示し、馬番の出現頻度を事前計算して
    LLMの数え間違いを防止する。
    """
    bet_type_names = {
        "win": "単勝",
        "place": "複勝",
        "quinella": "馬連",
        "quinella_place": "ワイド",
        "exacta": "馬単",
        "trio": "三連複",
        "trifecta": "三連単",
    }

    if not cart_items:
        return "カートは空です"

    lines = []
    horse_count: dict[int, int] = {}
    race_ids: dict[str, str] = {}  # race_id -> race_name
    total_amount = 0

    for i, item in enumerate(cart_items, 1):
        race_id = item.get("raceId", "")
        bet_type = item.get("betType", "")
        bet_type_display = bet_type_names.get(bet_type, bet_type)
        horse_numbers = item.get("horseNumbers", [])
        amount = item.get("amount", 0)
        race_name = item.get("raceName", "")

        if race_id:
            race_ids[race_id] = race_name

        display = "-".join(str(n) for n in horse_numbers)
        line = f"{i}. {race_name} {bet_type_display} {display} ¥{amount:,}"
        lines.append(line)
        total_amount += amount

        for hn in horse_numbers:
            horse_count[hn] = horse_count.get(hn, 0) + 1

    total_bets = len(cart_items)
    header = f"買い目一覧（全{total_bets}点、合計¥{total_amount:,}）"

    # 対象レースID一覧（ツール呼び出し用）
    race_id_lines = []
    for rid, rname in race_ids.items():
        race_id_lines.append(f"  {rname}: race_id={rid}")

    # 馬番出現頻度サマリー（LLMの数え間違い防止）
    freq_lines = []
    for hn in sorted(horse_count.keys()):
        count = horse_count[hn]
        freq_lines.append(f"  {hn}番: {total_bets}点中{count}点に出現")

    parts = [header]
    if race_id_lines:
        parts.append("")
        parts.append("対象レース:")
        parts.extend(race_id_lines)
    parts.append("")
    parts.extend(lines)
    if freq_lines:
        parts.append("")
        parts.append("馬番の出現頻度:")
        parts.extend(freq_lines)

    return "\n".join(parts)


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
