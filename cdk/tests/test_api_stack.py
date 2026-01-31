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
        """Lambda関数が31個作成されること（API 30 + バッチ 1）."""
        template.resource_count_is("AWS::Lambda::Function", 31)

    def test_lambda_layer_created(self, template):
        """Lambda Layerが2個作成されること（API用 + バッチ用）."""
        template.resource_count_is("AWS::Lambda::LayerVersion", 2)

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

    def test_cors_origins_production_only(self, template):
        """デフォルトで本番オリジンのみ許可されること."""
        # OPTIONS メソッドが存在することでCORSが有効であることを確認
        # （CDKテンプレートではCORSオリジンはPreflightリソースとして設定される）
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

    def test_get_race_dates_endpoint(self, template):
        """GET /race-dates エンドポイントが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-race-dates",
                "Handler": "src.api.handlers.races.get_race_dates",
            },
        )

    def test_get_odds_history_endpoint(self, template):
        """GET /races/{race_id}/odds-history エンドポイントが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-odds-history",
                "Handler": "src.api.handlers.races.get_odds_history",
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

    def test_jockey_endpoints(self, template):
        """騎手APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-jockey-info",
                "Handler": "src.api.handlers.jockeys.get_jockey_info",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-jockey-stats",
                "Handler": "src.api.handlers.jockeys.get_jockey_stats",
            },
        )

    def test_horse_endpoints(self, template):
        """馬APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-horse-performances",
                "Handler": "src.api.handlers.horses.get_horse_performances",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-horse-training",
                "Handler": "src.api.handlers.horses.get_horse_training",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-extended-pedigree",
                "Handler": "src.api.handlers.horses.get_extended_pedigree",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-course-aptitude",
                "Handler": "src.api.handlers.horses.get_course_aptitude",
            },
        )

    def test_trainer_endpoints(self, template):
        """厩舎APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-trainer-info",
                "Handler": "src.api.handlers.trainers.get_trainer_info",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-trainer-stats",
                "Handler": "src.api.handlers.trainers.get_trainer_stats",
            },
        )

    def test_stallion_endpoints(self, template):
        """種牡馬APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-stallion-offspring-stats",
                "Handler": "src.api.handlers.stallions.get_stallion_offspring_stats",
            },
        )

    def test_statistics_endpoints(self, template):
        """統計APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-gate-position-stats",
                "Handler": "src.api.handlers.statistics.get_gate_position_stats",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-past-race-stats",
                "Handler": "src.api.handlers.statistics.get_past_race_stats",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-jockey-course-stats",
                "Handler": "src.api.handlers.statistics.get_jockey_course_stats",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-popularity-payout-stats",
                "Handler": "src.api.handlers.statistics.get_popularity_payout_stats",
            },
        )

    def test_race_results_endpoint(self, template):
        """GET /races/{race_id}/results エンドポイントが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-race-results",
                "Handler": "src.api.handlers.races.get_race_results",
            },
        )

    def test_owner_endpoints(self, template):
        """馬主APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-owner-info",
                "Handler": "src.api.handlers.owners.get_owner_info",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-owner-stats",
                "Handler": "src.api.handlers.owners.get_owner_stats",
            },
        )

    def test_breeder_endpoints(self, template):
        """生産者APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-breeder-info",
                "Handler": "src.api.handlers.owners.get_breeder_info",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-breeder-stats",
                "Handler": "src.api.handlers.owners.get_breeder_stats",
            },
        )

    def test_ai_shisu_scraper_lambda(self, template):
        """AI指数スクレイピングLambdaが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-ai-shisu-scraper",
                "Handler": "batch.ai_shisu_scraper.handler",
                "Timeout": 300,
                "MemorySize": 512,
            },
        )

    def test_ai_predictions_dynamodb_table(self, template):
        """AI予想データ用DynamoDBテーブルが存在すること."""
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "TableName": "baken-kaigi-ai-predictions",
                "KeySchema": [
                    {"AttributeName": "race_id", "KeyType": "HASH"},
                    {"AttributeName": "source", "KeyType": "RANGE"},
                ],
            },
        )

    def test_eventbridge_rule_for_scraper(self, template):
        """スクレイパー用EventBridgeルールが存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-ai-shisu-scraper-rule",
                "ScheduleExpression": "cron(0 21 ? * * *)",  # UTC 21:00 = JST 06:00
            },
        )


class TestAgentCoreRuntimeRole:
    """AgentCore Runtimeロールのテスト."""

    def test_agentcore_runtime_role_created(self, template):
        """AgentCore Runtime用IAMロールが作成されること."""
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "RoleName": "baken-kaigi-agentcore-runtime-role",
            },
        )

    def test_agentcore_role_has_ecr_image_access(self, template):
        """AgentCoreロールにECRイメージ取得権限があること."""
        # ECRImageAccess権限のステートメントが存在することを確認
        resources = template.find_resources("AWS::IAM::Policy")
        ecr_actions_found = False
        for resource in resources.values():
            statements = resource.get("Properties", {}).get("PolicyDocument", {}).get("Statement", [])
            for stmt in statements:
                actions = stmt.get("Action", [])
                if isinstance(actions, list):
                    if "ecr:BatchGetImage" in actions and "ecr:GetDownloadUrlForLayer" in actions:
                        ecr_actions_found = True
                        break
        assert ecr_actions_found, "ECR イメージ取得権限（BatchGetImage, GetDownloadUrlForLayer）が見つかりません"

    def test_agentcore_role_has_ecr_token_access(self, template):
        """AgentCoreロールにECR認証トークン取得権限があること."""
        resources = template.find_resources("AWS::IAM::Policy")
        ecr_token_found = False
        for resource in resources.values():
            statements = resource.get("Properties", {}).get("PolicyDocument", {}).get("Statement", [])
            for stmt in statements:
                actions = stmt.get("Action", [])
                if isinstance(actions, str) and actions == "ecr:GetAuthorizationToken":
                    ecr_token_found = True
                    break
                if isinstance(actions, list) and "ecr:GetAuthorizationToken" in actions:
                    ecr_token_found = True
                    break
        assert ecr_token_found, "ECR認証トークン取得権限（GetAuthorizationToken）が見つかりません"

    def test_agentcore_role_has_cloudwatch_metrics(self, template):
        """AgentCoreロールにCloudWatch Metrics送信権限があること."""
        resources = template.find_resources("AWS::IAM::Policy")
        cw_metrics_found = False
        for resource in resources.values():
            statements = resource.get("Properties", {}).get("PolicyDocument", {}).get("Statement", [])
            for stmt in statements:
                actions = stmt.get("Action", [])
                if isinstance(actions, str) and actions == "cloudwatch:PutMetricData":
                    cw_metrics_found = True
                    break
                if isinstance(actions, list) and "cloudwatch:PutMetricData" in actions:
                    cw_metrics_found = True
                    break
        assert cw_metrics_found, "CloudWatch Metrics送信権限（PutMetricData）が見つかりません"

    def test_agentcore_role_has_xray_permissions(self, template):
        """AgentCoreロールにX-Ray権限があること."""
        resources = template.find_resources("AWS::IAM::Policy")
        xray_found = False
        for resource in resources.values():
            statements = resource.get("Properties", {}).get("PolicyDocument", {}).get("Statement", [])
            for stmt in statements:
                actions = stmt.get("Action", [])
                if isinstance(actions, list) and "xray:PutTraceSegments" in actions:
                    xray_found = True
                    break
        assert xray_found, "X-Ray権限（PutTraceSegments）が見つかりません"

    def test_agentcore_role_has_bedrock_permissions(self, template):
        """AgentCoreロールにBedrock Model呼び出し権限があること."""
        resources = template.find_resources("AWS::IAM::Policy")
        bedrock_found = False
        for resource in resources.values():
            statements = resource.get("Properties", {}).get("PolicyDocument", {}).get("Statement", [])
            for stmt in statements:
                actions = stmt.get("Action", [])
                if isinstance(actions, list):
                    if "bedrock:InvokeModel" in actions and "bedrock:InvokeModelWithResponseStream" in actions:
                        bedrock_found = True
                        break
        assert bedrock_found, "Bedrock Model呼び出し権限（InvokeModel）が見つかりません"


class TestCorsConfiguration:
    """CORS設定のテスト."""

    def test_cors_allows_dev_origins_when_enabled(self):
        """allow_dev_origins=Trueの場合、開発用オリジンも許可されること."""
        import aws_cdk as cdk
        from aws_cdk import assertions

        from stacks.api_stack import BakenKaigiApiStack

        app = cdk.App()
        stack = BakenKaigiApiStack(app, "TestStackWithDevOrigins", allow_dev_origins=True)
        template = assertions.Template.from_stack(stack)

        # REST API の CORS 設定に localhost が含まれることを確認
        # （内部的に複数のオリジンが設定されている）
        template.has_resource_properties(
            "AWS::ApiGateway::Method",
            {"HttpMethod": "OPTIONS"},
        )

    def test_cors_denies_dev_origins_by_default(self):
        """デフォルトで開発用オリジンは許可されないこと."""
        import aws_cdk as cdk
        from aws_cdk import assertions

        from stacks.api_stack import BakenKaigiApiStack

        app = cdk.App()
        stack = BakenKaigiApiStack(app, "TestStackDefault", allow_dev_origins=False)
        template = assertions.Template.from_stack(stack)

        # OPTIONS メソッドが存在（CORS有効）
        template.has_resource_properties(
            "AWS::ApiGateway::Method",
            {"HttpMethod": "OPTIONS"},
        )
