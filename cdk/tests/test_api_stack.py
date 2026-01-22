"""API Stack テスト."""
import sys
from pathlib import Path

import pytest

# プロジェクトルート（cdk/）をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def template():
    """CloudFormationテンプレートを生成."""
    import aws_cdk as cdk
    from aws_cdk import assertions

    from stacks.api_stack import BakenKaigiApiStack

    app = cdk.App()
    stack = BakenKaigiApiStack(app, "TestStack")
    return assertions.Template.from_stack(stack)


class TestApiStack:
    """APIスタックのテスト."""

    def test_lambda_functions_created(self, template):
        """Lambda関数が10個作成されること."""
        template.resource_count_is("AWS::Lambda::Function", 10)

    def test_lambda_layer_created(self, template):
        """Lambda Layerが1個作成されること."""
        template.resource_count_is("AWS::Lambda::LayerVersion", 1)

    def test_api_gateway_created(self, template):
        """API Gatewayが作成されること."""
        template.resource_count_is("AWS::ApiGateway::RestApi", 1)
        template.has_resource_properties(
            "AWS::ApiGateway::RestApi",
            {"Name": "baken-kaigi-api"},
        )

    def test_lambda_runtime(self, template):
        """Lambda関数がPython 3.12を使用すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"Runtime": "python3.12"},
        )

    def test_lambda_timeout(self, template):
        """Lambda関数のタイムアウトが30秒であること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"Timeout": 30},
        )

    def test_lambda_memory(self, template):
        """Lambda関数のメモリサイズが256MBであること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"MemorySize": 256},
        )

    def test_cors_enabled(self, template):
        """API GatewayでCORSが有効であること."""
        # OPTIONS メソッドが存在することでCORSが有効であることを確認
        template.has_resource_properties(
            "AWS::ApiGateway::Method",
            {"HttpMethod": "OPTIONS"},
        )

    def test_get_races_endpoint(self, template):
        """GET /races エンドポイントが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-races",
                "Handler": "src.api.handlers.races.get_races",
            },
        )

    def test_get_race_detail_endpoint(self, template):
        """GET /races/{race_id} エンドポイントが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-race-detail",
                "Handler": "src.api.handlers.races.get_race_detail",
            },
        )

    def test_cart_endpoints(self, template):
        """カートAPIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"FunctionName": "baken-kaigi-add-to-cart"},
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"FunctionName": "baken-kaigi-get-cart"},
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"FunctionName": "baken-kaigi-remove-from-cart"},
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"FunctionName": "baken-kaigi-clear-cart"},
        )

    def test_consultation_endpoints(self, template):
        """相談APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"FunctionName": "baken-kaigi-start-consultation"},
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"FunctionName": "baken-kaigi-send-message"},
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"FunctionName": "baken-kaigi-get-consultation"},
        )
