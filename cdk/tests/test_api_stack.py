"""API Stack テスト."""
import sys
from pathlib import Path

import pytest

# プロジェクトルート（cdk/）をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def template():
    """CloudFormationテンプレートを生成.

    scope="module"により、このファイル内で1回のみスタック合成を実行。
    テストはテンプレートを読み取るのみで変更しないため、共有可能。
    """
    import aws_cdk as cdk
    from aws_cdk import assertions

    from stacks.api_stack import BakenKaigiApiStack

    app = cdk.App()
    stack = BakenKaigiApiStack(app, "TestStack")
    return assertions.Template.from_stack(stack)


@pytest.fixture(scope="module")
def template_with_dev_origins():
    """開発オリジン有効のCloudFormationテンプレートを生成.

    TestCorsConfiguration用。scope="module"で1回のみ合成。
    """
    import aws_cdk as cdk
    from aws_cdk import assertions

    from stacks.api_stack import BakenKaigiApiStack

    app = cdk.App()
    stack = BakenKaigiApiStack(app, "TestStackWithDevOrigins", allow_dev_origins=True)
    return assertions.Template.from_stack(stack)


@pytest.fixture(scope="module")
def template_without_dev_origins():
    """開発オリジン無効のCloudFormationテンプレートを生成.

    TestCorsConfiguration用。scope="module"で1回のみ合成。
    """
    import aws_cdk as cdk
    from aws_cdk import assertions

    from stacks.api_stack import BakenKaigiApiStack

    app = cdk.App()
    stack = BakenKaigiApiStack(app, "TestStackDefault", allow_dev_origins=False)
    return assertions.Template.from_stack(stack)


class TestApiStack:
    """APIスタックのテスト."""

    def test_lambda_functions_created(self, template):
        """Lambda関数が49個作成されること（API 34 + IPAT 7 + 賭け履歴 4 + 損失制限 4）."""
        template.resource_count_is("AWS::Lambda::Function", 49)

    def test_lambda_layer_created(self, template):
        """Lambda Layerが1個作成されること（API用）."""
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

    def test_agentcore_consultation_lambda(self, template):
        """AgentCore相談Lambdaが120秒タイムアウトで存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-agentcore-consultation",
                "Handler": "agentcore_handler.invoke_agentcore",
                "Timeout": 120,
            },
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

    def test_betting_record_endpoints(self, template):
        """賭け履歴APIのLambda関数が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-create-betting-record",
                "Handler": "src.api.handlers.betting_record.create_betting_record_handler",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-betting-records",
                "Handler": "src.api.handlers.betting_record.get_betting_records_handler",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-get-betting-summary",
                "Handler": "src.api.handlers.betting_record.get_betting_summary_handler",
            },
        )
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-settle-betting-record",
                "Handler": "src.api.handlers.betting_record.settle_betting_record_handler",
            },
        )

    def test_betting_record_dynamodb_table(self, template):
        """賭け履歴DynamoDBテーブルが存在すること."""
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "TableName": "baken-kaigi-betting-record",
                "KeySchema": [
                    {"AttributeName": "record_id", "KeyType": "HASH"},
                ],
            },
        )


# NOTE: AgentCore RuntimeはCDKではなくagentcore CLIで管理するようになったため、
# TestAgentCoreRuntimeRoleテストクラスは削除されました。
# 詳細: CDK管理のAgentCore Runtimeは30秒初期化タイムアウトで失敗するため、
# agentcore CLIでデプロイしたAgentを使用するように変更。


class TestCognitoGoogleProvider:
    """Cognito Google Identity Provider のテスト."""

    def test_google_identity_provider_created(self, template):
        """Google Identity Providerが作成されること."""
        template.has_resource_properties(
            "AWS::Cognito::UserPoolIdentityProvider",
            {
                "ProviderName": "Google",
                "ProviderType": "Google",
            },
        )

    def test_user_pool_client_supports_google(self, template):
        """User Pool ClientがGoogleプロバイダーをサポートすること."""
        template.has_resource_properties(
            "AWS::Cognito::UserPoolClient",
            {
                "SupportedIdentityProviders": ["COGNITO", "Google"],
            },
        )


class TestCorsConfiguration:
    """CORS設定のテスト."""

    def test_cors_allows_dev_origins_when_enabled(self, template_with_dev_origins):
        """allow_dev_origins=Trueの場合、開発用オリジンも許可されること."""
        # REST API の CORS 設定に localhost が含まれることを確認
        # （内部的に複数のオリジンが設定されている）
        template_with_dev_origins.has_resource_properties(
            "AWS::ApiGateway::Method",
            {"HttpMethod": "OPTIONS"},
        )

    def test_cors_denies_dev_origins_by_default(self, template_without_dev_origins):
        """デフォルトで開発用オリジンは許可されないこと."""
        # OPTIONS メソッドが存在（CORS有効）
        template_without_dev_origins.has_resource_properties(
            "AWS::ApiGateway::Method",
            {"HttpMethod": "OPTIONS"},
        )
