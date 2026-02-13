"""API レスポンスユーティリティ."""
import json
import os
from typing import Any

ALLOWED_ORIGINS = [
    "https://bakenkaigi.com",
    "https://www.bakenkaigi.com",
]

CORS_ALLOW_HEADERS = "Content-Type,Authorization,x-api-key,X-Guest-Id"
CORS_ALLOW_METHODS = "GET,POST,PUT,DELETE,OPTIONS"

if os.environ.get("ALLOW_DEV_ORIGINS") == "true":
    ALLOWED_ORIGINS.extend([
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ])


def get_cors_origin(event: dict | None = None) -> str:
    """リクエストの Origin ヘッダーから許可するオリジンを返す."""
    if event:
        headers = event.get("headers") or {}
        origin = headers.get("origin") or headers.get("Origin") or ""
        if origin in ALLOWED_ORIGINS:
            return origin
    return ALLOWED_ORIGINS[0]


def success_response(body: Any, status_code: int = 200, event: dict | None = None) -> dict:
    """成功レスポンスを生成する.

    Args:
        body: レスポンスボディ
        status_code: HTTPステータスコード
        event: API Gatewayイベント（CORS Origin判定用）

    Returns:
        API Gatewayレスポンス形式の辞書
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": get_cors_origin(event),
            "Access-Control-Allow-Headers": CORS_ALLOW_HEADERS,
            "Access-Control-Allow-Methods": CORS_ALLOW_METHODS,
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def error_response(
    message: str, status_code: int = 400, error_code: str | None = None, event: dict | None = None,
) -> dict:
    """エラーレスポンスを生成する.

    Args:
        message: エラーメッセージ
        status_code: HTTPステータスコード
        error_code: エラーコード
        event: API Gatewayイベント（CORS Origin判定用）

    Returns:
        API Gatewayレスポンス形式の辞書
    """
    body = {"error": {"message": message}}
    if error_code:
        body["error"]["code"] = error_code

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": get_cors_origin(event),
            "Access-Control-Allow-Headers": CORS_ALLOW_HEADERS,
            "Access-Control-Allow-Methods": CORS_ALLOW_METHODS,
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def not_found_response(resource: str = "Resource", event: dict | None = None) -> dict:
    """404 Not Foundレスポンスを生成する."""
    return error_response(f"{resource} not found", status_code=404, error_code="NOT_FOUND", event=event)


def bad_request_response(message: str, event: dict | None = None) -> dict:
    """400 Bad Requestレスポンスを生成する."""
    return error_response(message, status_code=400, error_code="BAD_REQUEST", event=event)


def internal_error_response(message: str = "Internal server error", event: dict | None = None) -> dict:
    """500 Internal Server Errorレスポンスを生成する."""
    return error_response(message, status_code=500, error_code="INTERNAL_ERROR", event=event)


def unauthorized_response(message: str = "Authentication required", event: dict | None = None) -> dict:
    """401 Unauthorizedレスポンスを生成する."""
    return error_response(message, status_code=401, error_code="UNAUTHORIZED", event=event)


def forbidden_response(message: str = "Access denied", event: dict | None = None) -> dict:
    """403 Forbiddenレスポンスを生成する."""
    return error_response(message, status_code=403, error_code="FORBIDDEN", event=event)


def conflict_response(message: str = "Resource already exists", event: dict | None = None) -> dict:
    """409 Conflictレスポンスを生成する."""
    return error_response(message, status_code=409, error_code="CONFLICT", event=event)


def created_response(body: Any, event: dict | None = None) -> dict:
    """201 Createdレスポンスを生成する."""
    return success_response(body, status_code=201, event=event)
