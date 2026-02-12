"""AgentCore相談APIハンドラーのテスト."""
import json
from unittest.mock import MagicMock, patch

from botocore.exceptions import BotoCoreError, ClientError

from src.api.handlers.agentcore_consultation import invoke_agentcore
from src.domain.value_objects import BettingSummary
from src.domain.value_objects.money import Money


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


class TestInvokeAgentcoreBodyValidation:
    """invoke_agentcore のボディバリデーションテスト."""

    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_ボディが数値JSONの場合400エラー(self) -> None:
        """ボディがJSONオブジェクトでない場合400エラーになることを確認."""
        event = {"body": "123"}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 400

    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_ボディが配列JSONの場合400エラー(self) -> None:
        """ボディがJSON配列の場合400エラーになることを確認."""
        event = {"body": '[1, 2, 3]'}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 400


class TestInvokeAgentcoreSuggestedQuestions:
    """invoke_agentcore の suggested_questions レスポンステスト."""

    @patch("src.api.handlers.agentcore_consultation.boto3")
    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_非空のsuggested_questionsがレスポンスに含まれる(self, mock_boto3) -> None:
        """AgentCoreが非空のsuggested_questionsを返した場合、レスポンスに含まれる."""
        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": [
                {
                    "message": "分析結果です",
                    "session_id": "test-sq",
                    "suggested_questions": ["質問1？", "質問2？"],
                }
            ],
        }
        mock_boto3.client.return_value = mock_client

        event = {"body": json.dumps({"prompt": "分析して", "type": "consultation"})}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["suggested_questions"] == ["質問1？", "質問2？"]

    @patch("src.api.handlers.agentcore_consultation.boto3")
    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_空のsuggested_questionsはレスポンスに含まれない(self, mock_boto3) -> None:
        """AgentCoreが空のsuggested_questionsを返した場合、レスポンスに含まれない."""
        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": [
                {
                    "message": "結果",
                    "session_id": "test-empty",
                    "suggested_questions": [],
                }
            ],
        }
        mock_boto3.client.return_value = mock_client

        event = {"body": json.dumps({"prompt": "テスト", "type": "consultation"})}
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "suggested_questions" not in body


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


class TestInvokeAgentcoreBettingSummary:
    """invoke_agentcore の成績サマリー注入テスト."""

    def _make_event(self, prompt="テスト", user_id=None):
        """テスト用イベントを作成する."""
        event = {"body": json.dumps({"prompt": prompt})}
        if user_id:
            event["requestContext"] = {
                "authorizer": {"claims": {"sub": user_id}}
            }
        return event

    def _make_summary(self, record_count=10, win_rate=0.25, roi=85.0, net_profit=-1500):
        """テスト用BettingSummaryを作成する."""
        total_investment = 10000
        total_payout = total_investment + net_profit
        return BettingSummary(
            total_investment=Money.of(total_investment),
            total_payout=Money.of(total_payout),
            net_profit=net_profit,
            win_rate=win_rate,
            record_count=record_count,
            roi=roi,
        )

    @patch("src.api.handlers.agentcore_consultation.boto3")
    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    @patch("src.api.handlers.agentcore_consultation.GetBettingSummaryUseCase")
    def test_認証済みユーザーの成績がペイロードに含まれる(
        self, mock_use_case_cls, mock_boto3
    ) -> None:
        """認証済みユーザーの成績サマリーがAgentCoreペイロードに注入される."""
        summary = self._make_summary()
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = summary
        mock_use_case_cls.return_value = mock_use_case

        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": [{"message": "分析結果", "session_id": "s1"}],
        }
        mock_boto3.client.return_value = mock_client

        event = self._make_event(user_id="user-123")
        invoke_agentcore(event, None)

        # invoke_agent_runtime に渡されたペイロードを検証
        call_kwargs = mock_client.invoke_agent_runtime.call_args
        payload = json.loads(call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload"))
        assert "betting_summary" in payload
        assert payload["betting_summary"]["record_count"] == 10
        assert payload["betting_summary"]["win_rate"] == 25.0
        assert payload["betting_summary"]["roi"] == 85.0
        assert payload["betting_summary"]["net_profit"] == -1500

    @patch("src.api.handlers.agentcore_consultation.boto3")
    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    def test_未認証ユーザーの場合betting_summaryは含まれない(
        self, mock_boto3
    ) -> None:
        """未認証ユーザーの場合、betting_summaryはペイロードに含まれない."""
        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": [{"message": "結果", "session_id": "s2"}],
        }
        mock_boto3.client.return_value = mock_client

        event = self._make_event()  # user_idなし
        invoke_agentcore(event, None)

        call_kwargs = mock_client.invoke_agent_runtime.call_args
        payload = json.loads(call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload"))
        assert "betting_summary" not in payload

    @patch("src.api.handlers.agentcore_consultation.boto3")
    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    @patch("src.api.handlers.agentcore_consultation.GetBettingSummaryUseCase")
    def test_成績取得エラーでも相談は続行される(
        self, mock_use_case_cls, mock_boto3
    ) -> None:
        """成績取得に失敗しても相談自体は正常に完了する."""
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = Exception("DynamoDB error")
        mock_use_case_cls.return_value = mock_use_case

        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": [{"message": "結果", "session_id": "s3"}],
        }
        mock_boto3.client.return_value = mock_client

        event = self._make_event(user_id="user-456")
        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["message"] == "結果"

    @patch("src.api.handlers.agentcore_consultation.boto3")
    @patch("src.api.handlers.agentcore_consultation.AGENTCORE_AGENT_ARN", "arn:test")
    @patch("src.api.handlers.agentcore_consultation.GetBettingSummaryUseCase")
    def test_成績が0件の場合betting_summaryは含まれない(
        self, mock_use_case_cls, mock_boto3
    ) -> None:
        """成績が0件の場合、betting_summaryはペイロードに含まれない."""
        summary = self._make_summary(record_count=0, win_rate=0.0, roi=0.0, net_profit=0)
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = summary
        mock_use_case_cls.return_value = mock_use_case

        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": [{"message": "結果", "session_id": "s4"}],
        }
        mock_boto3.client.return_value = mock_client

        event = self._make_event(user_id="user-new")
        invoke_agentcore(event, None)

        call_kwargs = mock_client.invoke_agent_runtime.call_args
        payload = json.loads(call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload"))
        assert "betting_summary" not in payload
