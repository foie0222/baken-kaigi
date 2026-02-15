"""AgentCore 相談 API ハンドラー.

AgentCore Runtime にリクエストをプロキシし、利用制限を管理する。
このファイルは他のバックエンドモジュールに依存せず、独立して動作する。
"""
import base64
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
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

# 利用制限テーブル
USAGE_TRACKING_TABLE_NAME = os.environ.get("USAGE_TRACKING_TABLE_NAME")

# 利用制限: tier ごとの1日あたりの最大レース数
_TIER_LIMITS = {
    "anonymous": 1,
    "free": 3,
    "premium": None,  # 無制限
}

# JST タイムゾーン
_JST = timezone(timedelta(hours=9))

# ゲストID のバリデーションパターン（UUID形式）
_GUEST_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

# DynamoDB リソース（Lambda 実行間で再利用）
_dynamodb_resource = None


def _get_dynamodb_table():
    """利用制限追跡テーブルのDynamoDBリソースを取得（コネクション再利用）."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", region_name=AWS_REGION)
    return _dynamodb_resource.Table(USAGE_TRACKING_TABLE_NAME)

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


def _identify_user(event: dict) -> tuple[str, str]:
    """リクエストからユーザーキーとtierを特定する.

    Returns:
        (user_key, tier): ユーザーキーとtier
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
                    tier = payload.get("custom:tier", "free")
                    if tier == "premium":
                        return f"user:{sub}", "premium"
                    return f"user:{sub}", "free"
        except (json.JSONDecodeError, UnicodeDecodeError, IndexError):
            logger.warning("Failed to decode JWT payload")

    # X-Guest-Id ヘッダーからゲストIDを取得（UUID形式のみ受け入れ）
    guest_id = headers.get("X-Guest-Id") or headers.get("x-guest-id") or ""
    if guest_id and _GUEST_ID_PATTERN.match(guest_id):
        return f"guest:{guest_id}", "anonymous"

    # どちらもない場合は匿名扱い
    return "guest:unknown", "anonymous"


def _get_jst_date() -> str:
    """現在のJST日付を文字列で返す (例: '2026-02-13')."""
    return datetime.now(_JST).strftime("%Y-%m-%d")


def _extract_race_ids(body: dict) -> set[str]:
    """リクエストボディからレースIDのユニークセットを抽出する."""
    race_ids: set[str] = set()

    # prompt からレースIDを抽出（12桁数字パターン: YYYYMMDDVVRR）
    prompt = body.get("prompt", "")
    for match in re.findall(r"\d{12}", prompt):
        race_ids.add(match)

    return race_ids


def _check_and_record_usage(
    user_key: str,
    tier: str,
    race_ids: set[str],
    date: str,
) -> dict | None:
    """利用制限をチェックし、許可された場合は利用を記録する.

    Returns:
        None: 利用可能
        dict: 利用制限超過時のエラーレスポンスボディ
    """
    if not USAGE_TRACKING_TABLE_NAME:
        return None  # テーブル未設定時はスキップ

    max_races = _TIER_LIMITS.get(tier)
    if max_races is None:
        # 無制限（premium）
        return None

    table = _get_dynamodb_table()

    # 既存の利用状況を取得
    try:
        resp = table.get_item(Key={"user_key": user_key, "date": date})
    except ClientError:
        logger.exception("Usage tracking table read error")
        return None  # DB障害時は許可（フェイルオープン）

    item = resp.get("Item", {})
    existing_races: set[str] = set(item.get("consulted_race_ids", []) or [])

    # 新規レースのみ抽出（既に相談済みのレースはカウントしない）
    new_races = race_ids - existing_races

    if not new_races:
        # すべて既存のレース → 制限チェック不要
        return None

    # 新規レースを追加した場合の合計が制限を超えるか
    total_after = len(existing_races) + len(new_races)
    if total_after > max_races:
        consulted = len(existing_races)
        usage = {
            "consulted_races": consulted,
            "max_races": max_races,
            "remaining_races": max(0, max_races - consulted),
            "tier": tier,
        }
        return {
            "error": {
                "message": "本日の予想枠を使い切りました",
                "code": "RATE_LIMIT_EXCEEDED",
            },
            "usage": usage,
        }

    # 利用を記録
    ttl = int(time.time()) + 48 * 3600  # 48時間後
    updated_races = existing_races | new_races

    try:
        table.put_item(Item={
            "user_key": user_key,
            "date": date,
            "consulted_race_ids": updated_races,
            "ttl": ttl,
        })
    except ClientError:
        logger.exception("Usage tracking table write error")
        # 書き込み失敗でも処理は続行

    return None


def _make_usage_info(user_key: str, tier: str, date: str) -> dict | None:
    """現在の利用状況を取得する."""
    if not USAGE_TRACKING_TABLE_NAME:
        return None

    max_races = _TIER_LIMITS.get(tier)
    if max_races is None:
        return {"consulted_races": 0, "max_races": 0, "remaining_races": 0, "tier": "premium"}

    table = _get_dynamodb_table()

    try:
        resp = table.get_item(Key={"user_key": user_key, "date": date})
    except ClientError:
        return None

    item = resp.get("Item", {})
    consulted = len(set(item.get("consulted_race_ids", []) or []))
    return {
        "consulted_races": consulted,
        "max_races": max_races,
        "remaining_races": max(0, max_races - consulted),
        "tier": tier,
    }


def invoke_agentcore(event: dict, context: Any) -> dict:
    """AgentCore にリクエストを送信する.

    POST /api/consultation

    Request Body:
        prompt: ユーザーメッセージ
        race_id: レースID（オプション）
        session_id: セッションID（オプション）
        agent_data: エージェント育成データ（オプション）

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

    # ========================================
    # 利用制限チェック
    # ========================================
    user_key, tier = _identify_user(event)
    existing_session_id = body.get("session_id")

    # セッション継続（session_id あり）の場合は制限チェックスキップ
    if not existing_session_id:
        race_ids = _extract_race_ids(body)
        if race_ids:
            jst_date = _get_jst_date()
            limit_error = _check_and_record_usage(user_key, tier, race_ids, jst_date)
            if limit_error:
                return _make_response(limit_error, 429, event=event)

    # セッション ID（既存または新規生成）
    session_id = existing_session_id or str(uuid.uuid4())

    # AgentCore 用のペイロードを構築
    payload = {
        "prompt": body.get("prompt", ""),
        "race_id": body.get("race_id", ""),
    }

    # エージェントデータを中継
    agent_data = body.get("agent_data")
    if agent_data and isinstance(agent_data, dict):
        payload["agent_data"] = agent_data

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

        # 利用状況をレスポンスに付与
        usage = _make_usage_info(user_key, tier, _get_jst_date())
        if usage:
            response_body["usage"] = usage

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
