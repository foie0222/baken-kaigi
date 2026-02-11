"""EC2 スケジューラー テスト."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# プロジェクトルート（cdk/）をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


# ========================================
# Lambda ハンドラーのユニットテスト
# ========================================
class TestEc2SchedulerHandler:
    """EC2 スケジューラー Lambda ハンドラーのテスト."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """テストごとに環境変数と boto3 モックをセットアップする."""
        os.environ["INSTANCE_ID"] = "i-1234567890abcdef0"
        with patch(
            "boto3.client"
        ) as mock_client:
            self.mock_ec2 = MagicMock()
            mock_client.return_value = self.mock_ec2
            # handler モジュールをリロードしてモックを適用
            import importlib
            lambda_path = Path(__file__).parent.parent / "lambda" / "ec2_scheduler"
            sys.path.insert(0, str(lambda_path))
            import handler as handler_module
            importlib.reload(handler_module)
            self.handler = handler_module.handler
            yield
            sys.path.remove(str(lambda_path))

    def test_startアクションでインスタンスを起動する(self):
        event = {"action": "start"}
        result = self.handler(event, None)

        self.mock_ec2.start_instances.assert_called_once_with(
            InstanceIds=["i-1234567890abcdef0"]
        )
        assert result["status"] == "starting"
        assert result["instance_id"] == "i-1234567890abcdef0"

    def test_stopアクションでインスタンスを停止する(self):
        event = {"action": "stop"}
        result = self.handler(event, None)

        self.mock_ec2.stop_instances.assert_called_once_with(
            InstanceIds=["i-1234567890abcdef0"]
        )
        assert result["status"] == "stopping"
        assert result["instance_id"] == "i-1234567890abcdef0"

    def test_不明なアクションでエラーを返す(self):
        event = {"action": "restart"}
        result = self.handler(event, None)

        assert result["status"] == "error"
        assert "Unknown action: restart" in result["message"]
        self.mock_ec2.start_instances.assert_not_called()
        self.mock_ec2.stop_instances.assert_not_called()

    def test_アクション未指定でエラーを返す(self):
        event = {}
        result = self.handler(event, None)

        assert result["status"] == "error"
        assert "Unknown action: " in result["message"]


# ========================================
# CDK スタックのテスト
# ========================================
class TestEc2SchedulerStack:
    """EC2 スケジューラーの CDK リソーステスト."""

    @pytest.fixture(scope="class")
    def template(self):
        """JraVanServerStack の CloudFormation テンプレートを生成する."""
        import aws_cdk as cdk
        from aws_cdk import assertions

        from stacks.jravan_server_stack import JraVanServerStack

        app = cdk.App()
        stack = JraVanServerStack(app, "TestSchedulerStack")
        return assertions.Template.from_stack(stack)

    def test_スケジューラーLambda関数が作成される(self, template):
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "jravan-ec2-scheduler",
                "Runtime": "python3.12",
                "Handler": "handler.handler",
                "Timeout": 30,
            },
        )

    def test_Lambda環境変数にINSTANCE_IDが設定される(self, template):
        from aws_cdk import assertions

        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "jravan-ec2-scheduler",
                "Environment": {
                    "Variables": {
                        "INSTANCE_ID": assertions.Match.any_value(),
                    },
                },
            },
        )

    def test_起動スケジュールルールが作成される(self, template):
        from aws_cdk import assertions

        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "jravan-ec2-start",
                "ScheduleExpression": "cron(0 21 ? * FRI *)",
                "State": "ENABLED",
            },
        )

    def test_停止スケジュールルールが作成される(self, template):
        from aws_cdk import assertions

        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "jravan-ec2-stop",
                "ScheduleExpression": "cron(0 14 ? * SUN *)",
                "State": "ENABLED",
            },
        )

    def test_Lambda実行ロールにEC2権限がある(self, template):
        from aws_cdk import assertions

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "Action": [
                                        "ec2:StartInstances",
                                        "ec2:StopInstances",
                                    ],
                                    "Effect": "Allow",
                                }
                            ),
                        ]
                    ),
                },
            },
        )
