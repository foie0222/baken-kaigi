"""API レスポンスユーティリティ."""
import json
import os
from typing import Any

ALLOWED_ORIGINS = [
    "https://bakenkaigi.com",
    "https://www.bakenkaigi.com",
]

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
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
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
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def not_found_response(resource: str = "Resource") -> dict:
    """404 Not Foundレスポンスを生成する."""
    return error_response(f"{resource} not found", status_code=404, error_code="NOT_FOUND")


def bad_request_response(message: str) -> dict:
    """400 Bad Requestレスポンスを生成する."""
    return error_response(message, status_code=400, error_code="BAD_REQUEST")


def internal_error_response(message: str = "Internal server error") -> dict:
    """500 Internal Server Errorレスポンスを生成する."""
    return error_response(message, status_code=500, error_code="INTERNAL_ERROR")


def unauthorized_response(message: str = "Authentication required") -> dict:
    """401 Unauthorizedレスポンスを生成する."""
    return error_response(message, status_code=401, error_code="UNAUTHORIZED")


def forbidden_response(message: str = "Access denied") -> dict:
    """403 Forbiddenレスポンスを生成する."""
    return error_response(message, status_code=403, error_code="FORBIDDEN")
