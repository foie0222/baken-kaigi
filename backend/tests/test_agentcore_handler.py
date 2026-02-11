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

    def test_suggested_questionsを展開できる(self):
        """ネストされたJSONからsuggested_questionsを展開できる."""
        from agentcore_handler import _unwrap_nested_json

        inner = json.dumps({
            "message": "分析結果",
            "session_id": "abc123",
            "suggested_questions": ["質問1？", "質問2？"],
        })
        result = {"message": inner}
        unwrapped = _unwrap_nested_json(result)

        assert unwrapped["message"] == "分析結果"
        assert unwrapped["suggested_questions"] == ["質問1？", "質問2？"]

    def test_suggested_questionsがない場合は追加されない(self):
        """ネストされたJSONにsuggested_questionsがない場合は追加されない."""
        from agentcore_handler import _unwrap_nested_json

        inner = json.dumps({"message": "応答", "session_id": "xyz"})
        result = {"message": inner}
        unwrapped = _unwrap_nested_json(result)

        assert "suggested_questions" not in unwrapped


class TestHandleResponse:
    """_handle_response 関数のテスト."""

    def test_handle_streaming_body(self):
        """StreamingBody を正しく読み取れる."""
        from agentcore_handler import _handle_response

        # StreamingBody をシミュレートするモック
        mock_streaming_body = MagicMock()
        mock_streaming_body.read.return_value = b'{"message": "streaming response", "session_id": "test-123"}'

        response = {
            "contentType": "application/json",
            "response": mock_streaming_body,
        }
        result = _handle_response(response)

        assert result["message"] == "streaming response"
        assert result["session_id"] == "test-123"
        mock_streaming_body.read.assert_called_once()
        mock_streaming_body.close.assert_called_once()

    def test_handle_streaming_body_with_nested_json(self):
        """StreamingBody 内のネストされたJSONを展開できる."""
        from agentcore_handler import _handle_response

        inner = json.dumps({"message": "nested message", "session_id": "nested-456"})
        outer = json.dumps({"message": inner})

        mock_streaming_body = MagicMock()
        mock_streaming_body.read.return_value = outer.encode("utf-8")

        response = {
            "contentType": "application/json",
            "response": mock_streaming_body,
        }
        result = _handle_response(response)

        assert result["message"] == "nested message"
        assert result["session_id"] == "nested-456"
        mock_streaming_body.close.assert_called_once()

    def test_handle_streaming_body_read_error(self):
        """StreamingBody 読み取りエラー時はエラーメッセージを返す."""
        from agentcore_handler import _handle_response

        mock_streaming_body = MagicMock()
        mock_streaming_body.read.side_effect = OSError("Connection reset")

        response = {
            "contentType": "application/json",
            "response": mock_streaming_body,
        }
        result = _handle_response(response)

        assert result["message"] == "応答を取得できませんでした"
        mock_streaming_body.close.assert_called_once()

    def test_handle_streaming_body_decode_error(self):
        """StreamingBody デコードエラー時はエラーメッセージを返す."""
        from agentcore_handler import _handle_response

        mock_streaming_body = MagicMock()
        # 不正なUTF-8バイト列
        mock_streaming_body.read.return_value = b'\x80\x81\x82'

        response = {
            "contentType": "application/json",
            "response": mock_streaming_body,
        }
        result = _handle_response(response)

        assert result["message"] == "応答を取得できませんでした"
        mock_streaming_body.close.assert_called_once()

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
            "response": ['{"message": "byte response"}'.encode("utf-8")],
        }
        result = _handle_response(response)

        assert result["message"] == "byte response"

    def test_handle_nested_json_in_bytes(self):
        """バイト内のネストされたJSONを展開できる."""
        from agentcore_handler import _handle_response

        inner = json.dumps({"message": "unwrapped message"})
        outer = json.dumps({"message": inner})

        response = {
            "contentType": "application/json",
            "response": [outer.encode("utf-8")],
        }
        result = _handle_response(response)

        assert result["message"] == "unwrapped message"

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

    def test_cors_headers_default(self):
        """event未指定時はデフォルトの本番オリジンを返す."""
        from agentcore_handler import _make_response

        response = _make_response({})

        assert response["headers"]["Access-Control-Allow-Origin"] == "https://bakenkaigi.com"

    def test_cors_headers_with_allowed_origin(self):
        """許可されたオリジンがeventに含まれる場合はそのオリジンを返す."""
        from agentcore_handler import _make_response

        event = {"headers": {"origin": "https://www.bakenkaigi.com"}}
        response = _make_response({}, event=event)

        assert response["headers"]["Access-Control-Allow-Origin"] == "https://www.bakenkaigi.com"

    def test_cors_headers_with_disallowed_origin(self):
        """許可されていないオリジンの場合はデフォルトオリジンを返す."""
        from agentcore_handler import _make_response

        event = {"headers": {"origin": "https://evil.example.com"}}
        response = _make_response({}, event=event)

        assert response["headers"]["Access-Control-Allow-Origin"] == "https://bakenkaigi.com"


class TestInvokeAgentcore:
    """invoke_agentcore 関数のテスト."""

    def test_returns_500_when_agentcore_arn_not_set(self):
        """AGENTCORE_AGENT_ARN 環境変数が未設定の場合は500エラーを返す."""
        with patch("agentcore_handler.AGENTCORE_AGENT_ARN", None):
            from agentcore_handler import invoke_agentcore

            event = {"body": '{"prompt": "テスト"}'}
            context = MagicMock()

            response = invoke_agentcore(event, context)

            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert "AGENTCORE_AGENT_ARN" in body["error"]

    def test_returns_400_when_prompt_missing(self):
        """prompt が含まれていない場合は400エラーを返す."""
        with patch("agentcore_handler.AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test"):
            from agentcore_handler import invoke_agentcore

            event = {"body": '{"cart_items": []}'}
            context = MagicMock()

            response = invoke_agentcore(event, context)

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert "prompt is required" in body["error"]

    def test_returns_400_when_invalid_json_body(self):
        """不正なJSONボディの場合は400エラーを返す."""
        with patch("agentcore_handler.AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test"):
            from agentcore_handler import invoke_agentcore

            event = {"body": "invalid json"}
            context = MagicMock()

            response = invoke_agentcore(event, context)

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert "Invalid JSON" in body["error"]


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


class TestTypeフィールド中継:
    """invoke_agentcore が type フィールドを AgentCore に中継することの検証."""

    def test_typeフィールドがpayloadに含まれる(self):
        """type フィールドがリクエストボディに含まれる場合、payload に中継される."""
        with patch("agentcore_handler.AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test"):
            from agentcore_handler import invoke_agentcore

            body = {
                "prompt": "買い目を提案して",
                "type": "bet_proposal",
            }
            event = {"body": json.dumps(body)}
            context = MagicMock()

            mock_client = MagicMock()
            mock_streaming_body = MagicMock()
            mock_streaming_body.read.return_value = json.dumps(
                {"message": "提案結果", "session_id": "test-123"}
            ).encode("utf-8")
            mock_client.invoke_agent_runtime.return_value = {
                "contentType": "application/json",
                "response": mock_streaming_body,
            }

            with patch("agentcore_handler.boto3") as mock_boto3:
                mock_boto3.client.return_value = mock_client
                invoke_agentcore(event, context)

            # invoke_agent_runtime に渡された payload を検証
            call_args = mock_client.invoke_agent_runtime.call_args
            sent_payload = json.loads(call_args.kwargs["payload"])
            assert sent_payload["type"] == "bet_proposal"

    def test_type省略時はpayloadに含まれない(self):
        """type フィールドが省略された場合、payload に type は含まれない."""
        with patch("agentcore_handler.AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test"):
            from agentcore_handler import invoke_agentcore

            body = {
                "prompt": "この馬について教えて",
            }
            event = {"body": json.dumps(body)}
            context = MagicMock()

            mock_client = MagicMock()
            mock_streaming_body = MagicMock()
            mock_streaming_body.read.return_value = json.dumps(
                {"message": "分析結果", "session_id": "test-456"}
            ).encode("utf-8")
            mock_client.invoke_agent_runtime.return_value = {
                "contentType": "application/json",
                "response": mock_streaming_body,
            }

            with patch("agentcore_handler.boto3") as mock_boto3:
                mock_boto3.client.return_value = mock_client
                invoke_agentcore(event, context)

            call_args = mock_client.invoke_agent_runtime.call_args
            sent_payload = json.loads(call_args.kwargs["payload"])
            assert "type" not in sent_payload

    def test_suggested_questionsがレスポンスに含まれる(self):
        """AgentCoreがsuggested_questionsを返した場合、レスポンスに含まれる."""
        with patch("agentcore_handler.AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test"):
            from agentcore_handler import invoke_agentcore

            body = {"prompt": "分析して", "type": "consultation"}
            event = {"body": json.dumps(body)}
            context = MagicMock()

            mock_client = MagicMock()
            mock_streaming_body = MagicMock()
            mock_streaming_body.read.return_value = json.dumps({
                "message": "分析結果です",
                "session_id": "test-sq",
                "suggested_questions": ["追加質問1？", "追加質問2？"],
            }).encode("utf-8")
            mock_client.invoke_agent_runtime.return_value = {
                "contentType": "application/json",
                "response": mock_streaming_body,
            }

            with patch("agentcore_handler.boto3") as mock_boto3:
                mock_boto3.client.return_value = mock_client
                response = invoke_agentcore(event, context)

            assert response["statusCode"] == 200
            response_body = json.loads(response["body"])
            assert response_body["suggested_questions"] == ["追加質問1？", "追加質問2？"]

    def test_suggested_questionsが空の場合はレスポンスに含まれない(self):
        """AgentCoreがsuggested_questionsを空リストで返した場合、レスポンスに含まれない."""
        with patch("agentcore_handler.AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test"):
            from agentcore_handler import invoke_agentcore

            body = {"prompt": "テスト", "type": "consultation"}
            event = {"body": json.dumps(body)}
            context = MagicMock()

            mock_client = MagicMock()
            mock_streaming_body = MagicMock()
            mock_streaming_body.read.return_value = json.dumps({
                "message": "結果",
                "session_id": "test-empty",
                "suggested_questions": [],
            }).encode("utf-8")
            mock_client.invoke_agent_runtime.return_value = {
                "contentType": "application/json",
                "response": mock_streaming_body,
            }

            with patch("agentcore_handler.boto3") as mock_boto3:
                mock_boto3.client.return_value = mock_client
                response = invoke_agentcore(event, context)

            assert response["statusCode"] == 200
            response_body = json.loads(response["body"])
            assert "suggested_questions" not in response_body

    def test_不正なtype値は400エラー(self):
        """type に無効な値が指定された場合は400エラーを返す."""
        with patch("agentcore_handler.AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test"):
            from agentcore_handler import invoke_agentcore

            body = {
                "prompt": "テスト",
                "type": "invalid_type",
            }
            event = {"body": json.dumps(body)}
            context = MagicMock()

            response = invoke_agentcore(event, context)

            assert response["statusCode"] == 400
            response_body = json.loads(response["body"])
            assert "Invalid type" in response_body["error"]
