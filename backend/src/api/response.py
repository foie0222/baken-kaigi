"""API レスポンスユーティリティ."""
import json
from typing import Any


def success_response(body: Any, status_code: int = 200) -> dict:
    """成功レスポンスを生成する.

    Args:
        body: レスポンスボディ
        status_code: HTTPステータスコード

    Returns:
        API Gatewayレスポンス形式の辞書
    """
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


def error_response(message: str, status_code: int = 400, error_code: str | None = None) -> dict:
    """エラーレスポンスを生成する.

    Args:
        message: エラーメッセージ
        status_code: HTTPステータスコード
        error_code: エラーコード

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
            "Access-Control-Allow-Origin": "*",
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
