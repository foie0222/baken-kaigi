"""AgentCore相談APIハンドラーのテスト."""
import json
from unittest.mock import MagicMock, patch

from botocore.exceptions import BotoCoreError, ClientError

from src.api.handlers.agentcore_consultation import invoke_agentcore


class TestInvokeAgentcoreErrorHandling:
    """invoke_agentcore のエラーハンドリングテスト."""

    @patch("src.api.handlers.agentcore_consultation.boto3")
    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_ClientError時に安全なエラーメッセージを返す(self, mock_boto3) -> None:
        """ClientError発生時に内部エラー詳細がクライアントに漏洩しない."""
        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "User is not authorized"}},
            "InvokeAgentRuntime",
        )
        mock_boto3.client.return_value = mock_client

        event = {"body": json.dumps({"prompt": "テスト"})}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        # エラーメッセージに内部詳細が含まれていないことを確認
        assert "AccessDeniedException" not in body["error"]
        assert "AgentCore" in body["error"]

    @patch("src.api.handlers.agentcore_consultation.boto3")
    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_BotoCoreError時にloggerで記録される(self, mock_boto3) -> None:
        """BotoCoreError発生時にlogger.exceptionでスタックトレースが記録される."""
        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.side_effect = BotoCoreError()
        mock_boto3.client.return_value = mock_client

        event = {"body": json.dumps({"prompt": "テスト"})}

        with patch("src.api.handlers.agentcore_consultation.logger") as mock_logger:
            result = invoke_agentcore(event, None)

            assert result["statusCode"] == 500
            # logger.exception が呼ばれていることを確認
            mock_logger.exception.assert_called_once()


class TestInvokeAgentcoreTypeValidation:
    """invoke_agentcore の型バリデーションテスト."""

    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_promptが整数の場合400エラー(self) -> None:
        """promptが文字列でない場合400エラーになることを確認."""
        event = {"body": json.dumps({"prompt": 12345})}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "prompt" in body["error"]

    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_promptがリストの場合400エラー(self) -> None:
        """promptがリストの場合400エラーになることを確認."""
        event = {"body": json.dumps({"prompt": ["hello"]})}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "prompt" in body["error"]

    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_session_idが整数の場合400エラー(self) -> None:
        """session_idが文字列でない場合400エラーになることを確認."""
        event = {"body": json.dumps({"prompt": "テスト", "session_id": 12345})}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "session_id" in body["error"]

    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_cart_itemsが文字列の場合400エラー(self) -> None:
        """cart_itemsがリストでない場合400エラーになることを確認."""
        event = {"body": json.dumps({"prompt": "テスト", "cart_items": "invalid"})}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "cart_items" in body["error"]
