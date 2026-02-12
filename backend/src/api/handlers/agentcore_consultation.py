"""AgentCore 相談 API ハンドラー.

AgentCore Runtime にリクエストをプロキシする。
"""
import json
import logging
import os
import uuid
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from src.api.auth import get_authenticated_user_id
from src.application.use_cases.get_betting_summary import GetBettingSummaryUseCase

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# AgentCore Runtime の ARN（CDKで動的に設定される）
# Lambda実行時に環境変数から取得（テスト時はNoneでもインポート可能）
AGENTCORE_AGENT_ARN = os.environ.get("AGENTCORE_AGENT_ARN")

# AWS リージョン
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# CORS 許可オリジン
_ALLOWED_ORIGINS = [
    "https://bakenkaigi.com",
    "https://www.bakenkaigi.com",
]

if os.environ.get("ALLOW_DEV_ORIGINS") == "true":
    _ALLOWED_ORIGINS.extend([
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ])


def _get_cors_origin(event: dict | None = None) -> str:
    """リクエストの Origin ヘッダーから許可するオリジンを返す."""
    if event:
        headers = event.get("headers") or {}
        origin = headers.get("origin") or headers.get("Origin") or ""
        if origin in _ALLOWED_ORIGINS:
            return origin
    return _ALLOWED_ORIGINS[0]


def _make_response(body: Any, status_code: int = 200, event: dict | None = None) -> dict:
    """API Gateway レスポンスを生成."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": _get_cors_origin(event),
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def _get_body(event: dict) -> dict:
    """リクエストボディを取得."""
    body = event.get("body")
    if not body:
        return {}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON body: {e}")

    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object")

    return parsed


def _get_betting_summary(event: dict) -> dict | None:
    """認証済みユーザーの成績サマリーを取得する.

    成績取得に失敗しても相談を妨げないよう、エラー時はNoneを返す。
    """
    try:
        user_id = get_authenticated_user_id(event)
        if user_id is None:
            return None

        from src.api.dependencies import Dependencies

        repo = Dependencies.get_betting_record_repository()
        use_case = GetBettingSummaryUseCase(repo)
        summary = use_case.execute(str(user_id))

        if summary.record_count == 0:
            return None

        return {
            "record_count": summary.record_count,
            "win_rate": float(summary.win_rate * 100),
            "roi": float(summary.roi),
            "net_profit": int(summary.net_profit),
        }
    except Exception:
        logger.warning("Failed to get betting summary", exc_info=True)
        return None


def invoke_agentcore(event: dict, context: Any) -> dict:
    """AgentCore にリクエストを送信する.

    POST /api/consultation

    Request Body:
        prompt: ユーザーメッセージ
        cart_items: カート内容（オプション）
        session_id: セッションID（オプション）

    Returns:
        message: AI からの応答
        session_id: セッションID
    """
    # 環境変数チェック（Lambda実行時のみ必須）
    if not AGENTCORE_AGENT_ARN:
        logger.error("AGENTCORE_AGENT_ARN environment variable is not configured")
        return _make_response(
            {"error": "AGENTCORE_AGENT_ARN environment variable is not configured"},
            500,
            event=event,
        )

    try:
        body = _get_body(event)
    except ValueError as e:
        return _make_response({"error": str(e)}, 400, event=event)

    if "prompt" not in body:
        return _make_response({"error": "prompt is required"}, 400, event=event)

    if not isinstance(body["prompt"], str):
        return _make_response({"error": "prompt must be a string"}, 400, event=event)

    # session_id の型チェック（オプションだが指定時は文字列であること）
    if "session_id" in body and not isinstance(body["session_id"], str):
        return _make_response({"error": "session_id must be a string"}, 400, event=event)

    # cart_items の型チェック（オプションだが指定時はリストであること）
    if "cart_items" in body and not isinstance(body["cart_items"], list):
        return _make_response({"error": "cart_items must be a list"}, 400, event=event)

    # セッション ID（既存または新規生成）
    session_id = body.get("session_id") or str(uuid.uuid4())

    # AgentCore 用のペイロードを構築
    payload = {
        "prompt": body.get("prompt", ""),
        "cart_items": body.get("cart_items", []),
    }

    # 認証済みユーザーの成績サマリーを取得
    betting_summary = _get_betting_summary(event)
    if betting_summary is not None:
        payload["betting_summary"] = betting_summary

    try:
        # boto3 クライアント設定
        config = Config(
            read_timeout=120,
            connect_timeout=30,
            retries={"max_attempts": 2},
        )

        # AgentCore データプレーンエンドポイント
        data_plane_endpoint = f"https://bedrock-agentcore.{AWS_REGION}.amazonaws.com"

        # bedrock-agentcore クライアント
        client = boto3.client(
            "bedrock-agentcore",
            region_name=AWS_REGION,
            endpoint_url=data_plane_endpoint,
            config=config,
        )

        # InvokeAgentRuntime を呼び出す
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENTCORE_AGENT_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(payload, ensure_ascii=False),
            contentType="application/json",
        )

        # レスポンスを処理
        result = _handle_response(response)

        response_body = {
            "message": result.get("message", "応答を取得できませんでした"),
            "session_id": result.get("session_id", session_id),
        }
        suggested = result.get("suggested_questions")
        if suggested:
            response_body["suggested_questions"] = suggested

        return _make_response(response_body, event=event)

    except (BotoCoreError, ClientError):
        logger.exception("AgentCore invocation error")
        return _make_response({"error": "AgentCore invocation failed"}, 500, event=event)


def _handle_response(response: dict) -> dict:
    """AgentCore のレスポンスを処理する."""
    content_type = response.get("contentType", "")

    if "text/event-stream" in content_type:
        # ストリーミングレスポンス
        return _handle_streaming_response(response.get("response", []))
    else:
        # 通常レスポンス
        events = []
        for event in response.get("response", []):
            if isinstance(event, bytes):
                try:
                    decoded = event.decode("utf-8")
                    if decoded.startswith('"') and decoded.endswith('"'):
                        event = json.loads(decoded)
                    else:
                        event = decoded
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
            events.append(event)

        # レスポンスを結合
        if events:
            if isinstance(events[0], dict):
                return events[0]
            elif isinstance(events[0], str):
                try:
                    return json.loads(events[0])
                except json.JSONDecodeError:
                    return {"message": events[0]}

        return {"message": "応答を取得できませんでした"}


def _handle_streaming_response(response) -> dict:
    """ストリーミングレスポンスを処理する."""
    complete_text = ""

    for chunk in response:
        if isinstance(chunk, bytes):
            try:
                line = chunk.decode("utf-8")
                if line.startswith("data: "):
                    json_chunk = line[6:]
                    try:
                        parsed = json.loads(json_chunk)
                        if isinstance(parsed, str):
                            complete_text += parsed
                        elif isinstance(parsed, dict) and "text" in parsed:
                            complete_text += parsed["text"]
                    except json.JSONDecodeError:
                        complete_text += json_chunk
            except UnicodeDecodeError:
                continue

    return {"message": complete_text or "応答を取得できませんでした"}
