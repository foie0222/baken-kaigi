"""AgentCore 相談 API ハンドラー.

AgentCore Runtime にリクエストをプロキシする。
このファイルは他のバックエンドモジュールに依存せず、独立して動作する。
"""
import json
import logging
import os
import uuid
from typing import Any

import boto3
from botocore.config import Config

# Lambda環境でログを出力するための設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# AgentCore Runtime の ARN
AGENTCORE_AGENT_ARN = os.environ.get(
    "AGENTCORE_AGENT_ARN",
    "arn:aws:bedrock-agentcore:ap-northeast-1:688567287706:runtime/baken_kaigi_ai-dfTUpICY2G"
)

# AWS リージョン
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")


def _make_response(body: Any, status_code: int = 200) -> dict:
    """API Gateway レスポンスを生成."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
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
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON body: {e}")


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
    try:
        body = _get_body(event)
    except ValueError as e:
        return _make_response({"error": str(e)}, 400)

    if "prompt" not in body:
        return _make_response({"error": "prompt is required"}, 400)

    # セッション ID（既存または新規生成）
    session_id = body.get("session_id") or str(uuid.uuid4())

    # AgentCore 用のペイロードを構築
    payload = {
        "prompt": body.get("prompt", ""),
        "cart_items": body.get("cart_items", []),
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

        return _make_response({
            "message": message,
            "session_id": result.get("session_id", session_id),
        })

    except Exception as e:
        error_msg = str(e)
        logger.exception("AgentCore invocation error: %s", error_msg)
        return _make_response({"error": f"AgentCore invocation failed: {error_msg}"}, 500)


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
