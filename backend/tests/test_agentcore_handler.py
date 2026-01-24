"""agentcore_handler のユニットテスト."""

import json
from unittest.mock import MagicMock, patch

import pytest


# テスト対象モジュールをインポート
# Lambda 環境外でもテスト可能にするため、boto3 をモック化
@pytest.fixture
def mock_boto3():
    """boto3 をモック化."""
    with patch("agentcore_handler.boto3") as mock:
        yield mock


class TestUnwrapNestedJson:
    """_unwrap_nested_json 関数のテスト."""

    def test_unwrap_single_level(self):
        """1レベルのネストを展開できる."""
        from agentcore_handler import _unwrap_nested_json

        result = {"message": '{"message": "こんにちは", "session_id": "abc123"}'}
        unwrapped = _unwrap_nested_json(result)

        assert unwrapped["message"] == "こんにちは"
        assert unwrapped["session_id"] == "abc123"

    def test_unwrap_double_level(self):
        """2レベルのネストを展開できる."""
        from agentcore_handler import _unwrap_nested_json

        inner = json.dumps({"message": "実際のメッセージ", "session_id": "xyz"})
        outer = json.dumps({"message": inner})
        result = {"message": outer}

        unwrapped = _unwrap_nested_json(result)

        assert unwrapped["message"] == "実際のメッセージ"
        assert unwrapped["session_id"] == "xyz"

    def test_no_unwrap_needed(self):
        """ネストがない場合はそのまま返す."""
        from agentcore_handler import _unwrap_nested_json

        result = {"message": "通常のテキスト"}
        unwrapped = _unwrap_nested_json(result)

        assert unwrapped["message"] == "通常のテキスト"

    def test_invalid_json_not_unwrapped(self):
        """不正なJSONは展開しない."""
        from agentcore_handler import _unwrap_nested_json

        result = {"message": "{invalid json}"}
        unwrapped = _unwrap_nested_json(result)

        assert unwrapped["message"] == "{invalid json}"

    def test_json_without_message_key(self):
        """message キーがないJSONは展開しない."""
        from agentcore_handler import _unwrap_nested_json

        result = {"message": '{"data": "something"}'}
        unwrapped = _unwrap_nested_json(result)

        assert unwrapped["message"] == '{"data": "something"}'

    def test_max_depth_protection(self):
        """最大深度を超えるネストは途中で停止."""
        from agentcore_handler import _unwrap_nested_json

        # 10レベルのネストを作成（最大5レベルまで展開）
        msg = "深いメッセージ"
        for _ in range(10):
            msg = json.dumps({"message": msg})

        result = {"message": msg}
        unwrapped = _unwrap_nested_json(result)

        # 5レベル展開後もまだJSONが残っている
        assert unwrapped["message"].startswith("{")


class TestHandleResponse:
    """_handle_response 関数のテスト."""

    def test_handle_dict_event(self):
        """辞書イベントを処理できる."""
        from agentcore_handler import _handle_response

        response = {
            "contentType": "application/json",
            "response": [{"message": "レスポンス"}],
        }
        result = _handle_response(response)

        assert result["message"] == "レスポンス"

    def test_handle_bytes_event(self):
        """バイトイベントを処理できる."""
        from agentcore_handler import _handle_response

        response = {
            "contentType": "application/json",
            "response": [b'{"message": "バイトレスポンス"}'],
        }
        result = _handle_response(response)

        assert result["message"] == "バイトレスポンス"

    def test_handle_nested_json_in_bytes(self):
        """バイト内のネストされたJSONを展開できる."""
        from agentcore_handler import _handle_response

        inner = json.dumps({"message": "展開されたメッセージ"})
        outer = json.dumps({"message": inner})

        response = {
            "contentType": "application/json",
            "response": [outer.encode("utf-8")],
        }
        result = _handle_response(response)

        assert result["message"] == "展開されたメッセージ"

    def test_handle_empty_response(self):
        """空のレスポンスを処理できる."""
        from agentcore_handler import _handle_response

        response = {
            "contentType": "application/json",
            "response": [],
        }
        result = _handle_response(response)

        assert result["message"] == "応答を取得できませんでした"


class TestMakeResponse:
    """_make_response 関数のテスト."""

    def test_make_success_response(self):
        """成功レスポンスを生成できる."""
        from agentcore_handler import _make_response

        response = _make_response({"message": "成功"})

        assert response["statusCode"] == 200
        assert "application/json" in response["headers"]["Content-Type"]
        body = json.loads(response["body"])
        assert body["message"] == "成功"

    def test_make_error_response(self):
        """エラーレスポンスを生成できる."""
        from agentcore_handler import _make_response

        response = _make_response({"error": "エラー"}, 400)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "エラー"

    def test_cors_headers(self):
        """CORSヘッダーが含まれる."""
        from agentcore_handler import _make_response

        response = _make_response({})

        assert response["headers"]["Access-Control-Allow-Origin"] == "*"


class TestGetBody:
    """_get_body 関数のテスト."""

    def test_get_valid_body(self):
        """有効なJSONボディを取得できる."""
        from agentcore_handler import _get_body

        event = {"body": '{"prompt": "テスト"}'}
        body = _get_body(event)

        assert body["prompt"] == "テスト"

    def test_get_empty_body(self):
        """空のボディは空の辞書を返す."""
        from agentcore_handler import _get_body

        event = {"body": None}
        body = _get_body(event)

        assert body == {}

    def test_invalid_json_raises(self):
        """不正なJSONはValueErrorを発生."""
        from agentcore_handler import _get_body

        event = {"body": "invalid json"}

        with pytest.raises(ValueError):
            _get_body(event)
