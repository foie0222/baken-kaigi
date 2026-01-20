"""API リクエストユーティリティ."""
import json
from typing import Any
from urllib.parse import unquote


def get_path_parameter(event: dict, name: str) -> str | None:
    """パスパラメータを取得する.

    Args:
        event: Lambda イベント
        name: パラメータ名

    Returns:
        パラメータ値（存在しない場合はNone、URLデコード済み）
    """
    path_params = event.get("pathParameters") or {}
    value = path_params.get(name)
    if value is not None:
        # URLエンコードされている可能性があるのでデコード
        return unquote(value)
    return None


def get_query_parameter(event: dict, name: str, default: str | None = None) -> str | None:
    """クエリパラメータを取得する.

    Args:
        event: Lambda イベント
        name: パラメータ名
        default: デフォルト値

    Returns:
        パラメータ値
    """
    query_params = event.get("queryStringParameters") or {}
    return query_params.get(name, default)


def get_body(event: dict) -> dict[str, Any]:
    """リクエストボディを取得する.

    Args:
        event: Lambda イベント

    Returns:
        パースされたボディ（空の場合は空辞書）

    Raises:
        ValueError: JSONパースに失敗した場合
    """
    body = event.get("body")
    if not body:
        return {}

    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON body: {e}")


def get_header(event: dict, name: str) -> str | None:
    """ヘッダーを取得する（大文字小文字を区別しない）.

    Args:
        event: Lambda イベント
        name: ヘッダー名

    Returns:
        ヘッダー値
    """
    headers = event.get("headers") or {}
    # 大文字小文字を区別しない検索
    name_lower = name.lower()
    for key, value in headers.items():
        if key.lower() == name_lower:
            return value
    return None
