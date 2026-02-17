"""AgentCore 相談 API ハンドラー.

AgentCore Runtime にリクエストをプロキシする。
このファイルは他のバックエンドモジュールに依存せず、独立して動作する。
"""
import base64
import json
import logging
import os
import re
import uuid
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

# Lambda環境でログを出力するための設定
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
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Guest-Id",
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
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON body: {e}")


_GUEST_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _identify_user(event: dict) -> str:
    """リクエストからユーザーキーを特定する.

    Returns:
        user_key: ユーザーキー文字列
    """
    headers = event.get("headers") or {}

    # Authorization ヘッダーからJWTを解析
    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            # JWT payload部分をbase64デコード（署名検証はCognitoが実施済み）
            parts = token.split(".")
            if len(parts) >= 2:
                # base64urlデコード（パディング補完）
                payload_b64 = parts[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                sub = payload.get("sub", "")
                if sub:
                    return f"user:{sub}"
        except (json.JSONDecodeError, UnicodeDecodeError, IndexError):
            logger.warning("Failed to decode JWT payload")

    # X-Guest-Id ヘッダーからゲストIDを取得（UUID形式のみ受け入れ）
    guest_id = headers.get("X-Guest-Id") or headers.get("x-guest-id") or ""
    if guest_id and _GUEST_ID_PATTERN.match(guest_id):
        return f"guest:{guest_id}"

    # どちらもない場合は匿名扱い
    return "guest:unknown"


def invoke_agentcore(event: dict, context: Any) -> dict:
    """AgentCore にリクエストを送信する.

    POST /api/consultation

    Request Body:
        race_id: レースID
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

    race_id = body.get("race_id", "")
    if not race_id:
        return _make_response({"error": "race_id is required"}, 400, event=event)
    if not re.fullmatch(r"\d{12}", race_id):
        return _make_response({"error": "race_id must be a 12-digit number"}, 400, event=event)

    user_key = _identify_user(event)

    # セッション ID（既存または新規生成）
    session_id = body.get("session_id") or str(uuid.uuid4())

    # AgentCore 用のペイロードを構築
    payload = {
        "race_id": race_id,
        "user_id": user_key,
    }

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

        # レスポンスを処理（ネストされたJSONも展開済み）
        result = _handle_response(response)

        # session_id を結果から取得（展開時に抽出されている場合）
        session_id = result.get("session_id", session_id)

        # message を文字列に変換
        message = result.get("message", "応答を取得できませんでした")

        if isinstance(message, dict):
            # AgentCore の応答形式: {"role": "assistant", "content": [{"text": "..."}]}
            content = message.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                first_content = content[0]
                if isinstance(first_content, dict) and "text" in first_content:
                    message = first_content["text"]
                elif isinstance(first_content, str):
                    message = first_content
                else:
                    message = str(first_content)
            else:
                message = str(message)

        response_body = {
            "message": message,
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
    """AgentCore のレスポンスを処理する.

    Args:
        response: AgentCore からのレスポンス辞書

    Returns:
        処理済みのレスポンス辞書（message, session_id を含む）
    """
    content_type = response.get("contentType", "")

    if "text/event-stream" in content_type:
        # ストリーミングレスポンス
        return _handle_streaming_response(response.get("response", []))

    # 通常レスポンス - すべてのイベントをデコードして結合
    decoded_content = ""
    resp_obj = response.get("response")

    # StreamingBody の場合は .read() で全体を読み取る
    if hasattr(resp_obj, 'read'):
        try:
            raw_bytes = resp_obj.read()
            decoded_content = raw_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.exception("StreamingBody read error: %s", e)
        finally:
            # HTTPコネクションをプールに戻すためクローズ
            if hasattr(resp_obj, 'close'):
                resp_obj.close()

    # EventStream の場合は iterate して収集
    elif resp_obj is not None:
        try:
            for event in resp_obj:
                if isinstance(event, bytes):
                    try:
                        decoded_content += event.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                elif isinstance(event, str):
                    decoded_content += event
                elif isinstance(event, dict):
                    # 辞書が直接返ってきた場合
                    return _unwrap_nested_json(event)
        except (TypeError, StopIteration) as e:
            logger.warning("Response iteration error: %s", e)

    # デコードしたコンテンツをJSONとしてパース
    if decoded_content:
        try:
            result = json.loads(decoded_content)
            if isinstance(result, dict):
                return _unwrap_nested_json(result)
            return {"message": str(result)}
        except json.JSONDecodeError:
            return {"message": decoded_content}

    logger.warning("No content decoded from response")
    return {"message": "応答を取得できませんでした"}


def _unwrap_nested_json(result: dict) -> dict:
    """ネストされたJSONを再帰的に展開する.

    AgentCore のレスポンスは複数回JSONエンコードされている場合がある。
    例: {"message": "{\"message\": \"実際のテキスト\"}"}
    この関数は最大5レベルまでネストを展開する。

    Args:
        result: message フィールドを含む辞書

    Returns:
        展開済みの辞書。message と session_id が含まれる。
    """
    max_depth = 5  # 無限ループ防止
    for _ in range(max_depth):
        msg = result.get("message", "")
        if not isinstance(msg, str) or not msg.startswith("{"):
            break
        try:
            inner = json.loads(msg)
            if isinstance(inner, dict) and "message" in inner:
                result["message"] = inner["message"]
                if "session_id" in inner:
                    result["session_id"] = inner["session_id"]
                if "suggested_questions" in inner:
                    result["suggested_questions"] = inner["suggested_questions"]
            else:
                break
        except json.JSONDecodeError:
            break
    return result


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
