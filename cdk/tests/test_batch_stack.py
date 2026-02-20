"""Batch Stack テスト."""
import sys
from pathlib import Path

import pytest

# プロジェクトルート（cdk/）をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def template():
    """CloudFormationテンプレートを生成."""
    import aws_cdk as cdk
    from aws_cdk import assertions

    from stacks.batch_stack import BakenKaigiBatchStack

    app = cdk.App()
    stack = BakenKaigiBatchStack(app, "TestBatchStack")
    return assertions.Template.from_stack(stack)


class TestBatchStack:
    """バッチスタックのテスト."""

    def test_lambda_functions_created(self, template):
        """Lambda関数が12個作成されること（スクレイパー9 + チェックサム1 + 自動投票2）."""
        template.resource_count_is("AWS::Lambda::Function", 12)

    def test_lambda_layer_created(self, template):
        """Lambda Layerが1個作成されること（バッチ用）."""
        template.resource_count_is("AWS::Lambda::LayerVersion", 1)

    def test_eventbridge_rules_created(self, template):
        """EventBridgeルールが14個作成されること."""
        template.resource_count_is("AWS::Events::Rule", 14)

    def test_no_dynamodb_tables(self, template):
        """DynamoDBテーブルはバッチスタックに含まれないこと."""
        template.resource_count_is("AWS::DynamoDB::Table", 0)

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

    def test_muryou_keiba_ai_scraper_lambda(self, template):
        """無料競馬AIスクレイピングLambdaが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-muryou-keiba-ai-scraper",
                "Handler": "batch.muryou_keiba_ai_scraper.handler",
                "Timeout": 300,
                "MemorySize": 512,
            },
        )

    def test_jra_checksum_updater_lambda(self, template):
        """JRAチェックサム更新Lambdaが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-jra-checksum-updater",
                "Handler": "batch.jra_checksum_updater.handler",
                "Timeout": 300,
            },
        )

    def test_eventbridge_rule_for_ai_shisu(self, template):
        """AI指数スクレイパー用EventBridgeルール（夜）が存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-ai-shisu-scraper-rule",
                "ScheduleExpression": "cron(0 12 ? * * *)",
            },
        )

    def test_eventbridge_rule_for_ai_shisu_morning(self, template):
        """AI指数スクレイパー用EventBridgeルール（朝）が存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-ai-shisu-scraper-morning-rule",
                "ScheduleExpression": "cron(0 0 ? * * *)",
            },
        )

    def test_eventbridge_rule_for_muryou_morning(self, template):
        """無料競馬AIスクレイパー用EventBridgeルール（当日朝）が存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-muryou-keiba-ai-scraper-morning-rule",
                "ScheduleExpression": "cron(30 0 ? * * *)",
            },
        )

    def test_eventbridge_rule_for_muryou_evening(self, template):
        """無料競馬AIスクレイパー用EventBridgeルール（前日夜）が存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-muryou-keiba-ai-scraper-evening-rule",
                "ScheduleExpression": "cron(0 12 ? * * *)",
            },
        )

    def test_eventbridge_rule_for_jra_checksum(self, template):
        """JRAチェックサム更新用EventBridgeルールが存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-jra-checksum-updater-rule",
                "ScheduleExpression": "cron(10 21 ? * * *)",
            },
        )

    def test_scraper_has_predictions_table_env(self, template):
        """AI予想スクレイパーにテーブル名環境変数が設定されていること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-ai-shisu-scraper",
                "Environment": {
                    "Variables": {
                        "AI_PREDICTIONS_TABLE_NAME": "baken-kaigi-ai-predictions",
                    },
                },
            },
        )

    def test_speed_index_scraper_has_table_env(self, template):
        """スピード指数スクレイパーにテーブル名環境変数が設定されていること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-jiro8-speed-index-scraper",
                "Environment": {
                    "Variables": {
                        "SPEED_INDICES_TABLE_NAME": "baken-kaigi-speed-indices",
                    },
                },
            },
        )

    def test_auto_bet_executor_lambda(self, template):
        """自動投票 BetExecutor Lambda が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-auto-bet-executor",
                "Handler": "batch.auto_bet_executor.handler",
                "Timeout": 180,
            },
        )

    def test_auto_bet_orchestrator_lambda(self, template):
        """自動投票 Orchestrator Lambda が存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-auto-bet-orchestrator",
                "Handler": "batch.auto_bet_orchestrator.handler",
                "Timeout": 60,
            },
        )

    def test_auto_bet_orchestrator_rule(self, template):
        """自動投票 Orchestrator EventBridge ルールが存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-auto-bet-orchestrator-rule",
                "ScheduleExpression": "cron(0/15 0-7 ? * SAT,SUN *)",
            },
        )

    # ========================================
    # HRDB レーススクレイパー
    # ========================================

    def test_hrdb_race_scraperが作成される(self, template):
        """HRDBレーススクレイパーLambdaが存在すること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-hrdb-race-scraper",
                "Handler": "batch.hrdb_race_scraper.handler",
                "Timeout": 600,
                "MemorySize": 512,
            },
        )

    def test_hrdb_scraperのeveningルールが作成される(self, template):
        """HRDBスクレイパー用EventBridgeルール（夜）が存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-hrdb-race-scraper-evening-rule",
                "ScheduleExpression": "cron(0 12 ? * * *)",
            },
        )

    def test_hrdb_scraperのmorningルールが作成される(self, template):
        """HRDBスクレイパー用EventBridgeルール（朝）が存在すること."""
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Name": "baken-kaigi-hrdb-race-scraper-morning-rule",
                "ScheduleExpression": "cron(30 23 ? * * *)",
            },
        )

    def test_hrdb_scraperにテーブル名環境変数が設定される(self, template):
        """HRDBスクレイパーにRaces/Runnersテーブル名環境変数が設定されていること."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "baken-kaigi-hrdb-race-scraper",
                "Environment": {
                    "Variables": {
                        "RACES_TABLE_NAME": "baken-kaigi-races",
                        "RUNNERS_TABLE_NAME": "baken-kaigi-runners",
                    },
                },
            },
        )

