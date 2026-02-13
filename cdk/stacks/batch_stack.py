"""馬券会議 バッチ処理スタック.

スクレイパー Lambda + EventBridge ルールを管理する。
BakenKaigiApiStack から分離されたステートレスリソースのみ含む。
"""
from pathlib import Path

from aws_cdk import BundlingOptions, Duration, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_lambda as lambda_
from constructs import Construct


class BakenKaigiBatchStack(Stack):
    """馬券会議 バッチ処理スタック.

    AI予想・スピード指数・馬柱のスクレイピングバッチと
    JRA チェックサム更新バッチを管理する。
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc | None = None,
        jravan_api_url: str | None = None,
        **kwargs,
    ) -> None:
        """スタックを初期化する.

        Args:
            scope: CDK スコープ
            construct_id: コンストラクト ID
            vpc: VPC（JRA-VAN 連携時に必要）
            jravan_api_url: JRA-VAN API の URL（例: http://10.0.1.100:8000）
            **kwargs: その他のスタックパラメータ
        """
        super().__init__(scope, construct_id, **kwargs)

        project_root = Path(__file__).parent.parent.parent
        use_jravan = jravan_api_url is not None

        # ========================================
        # DynamoDB テーブル参照（既存テーブルを名前で参照）
        # ========================================
        ai_predictions_table = dynamodb.Table.from_table_name(
            self, "AiPredictionsTable", "baken-kaigi-ai-predictions"
        )
        speed_indices_table = dynamodb.Table.from_table_name(
            self, "SpeedIndicesTable", "baken-kaigi-speed-indices"
        )
        past_performances_table = dynamodb.Table.from_table_name(
            self, "PastPerformancesTable", "baken-kaigi-past-performances"
        )

        # ========================================
        # Lambda Layer（バッチ処理用依存関係）
        # ========================================
        batch_layer_path = project_root / "cdk" / "batch_layer"
        batch_deps_layer = lambda_.LayerVersion(
            self,
            "BatchDepsLayer",
            code=lambda_.Code.from_asset(
                str(batch_layer_path),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output/python",
                    ],
                ),
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Dependencies layer for batch processing (beautifulsoup4, requests)",
        )

        # バッチ Lambda 共通コード
        backend_code = lambda_.Code.from_asset(
            str(project_root / "backend"),
            exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
        )

        # NOTE: スクレイパー Lambda は外部サイトにHTTPアクセスするためVPC外に配置。
        # VPC設定はEC2にアクセスが必要な jra_checksum_updater にのみ適用する。

        # ========================================
        # AI予想スクレイパー Lambda
        # ========================================

        # AI指数スクレイピング Lambda
        ai_shisu_scraper_fn = lambda_.Function(
            self,
            "AiShisuScraperFunction",
            handler="batch.ai_shisu_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-ai-shisu-scraper",
            description="AI指数スクレイピング（ai-shisu.com / 毎晩21時に翌日分取得）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "AI_PREDICTIONS_TABLE_NAME": ai_predictions_table.table_name,
            },
        )
        ai_predictions_table.grant_write_data(ai_shisu_scraper_fn)

        # 競馬AI ATHENA スクレイパー
        keiba_ai_athena_scraper_fn = lambda_.Function(
            self,
            "KeibaAiAthenaScraperFunction",
            handler="batch.keiba_ai_athena_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-keiba-ai-athena-scraper",
            description="競馬AI ATHENA スクレイピング（keiba-ai.jp / 毎晩21時に翌日分取得）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "AI_PREDICTIONS_TABLE_NAME": ai_predictions_table.table_name,
            },
        )
        ai_predictions_table.grant_write_data(keiba_ai_athena_scraper_fn)

        # 競馬AIナビ スクレイパー
        keiba_ai_navi_scraper_fn = lambda_.Function(
            self,
            "KeibaAiNaviScraperFunction",
            handler="batch.keiba_ai_navi_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-keiba-ai-navi-scraper",
            description="競馬AIナビ スクレイピング（horse-racing-ai-navi.com / 毎晩21時に翌日分取得）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "AI_PREDICTIONS_TABLE_NAME": ai_predictions_table.table_name,
            },
        )
        ai_predictions_table.grant_write_data(keiba_ai_navi_scraper_fn)

        # 競馬AIうままっくす スクレイパー
        umamax_scraper_fn = lambda_.Function(
            self,
            "UmamaxScraperFunction",
            handler="batch.umamax_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-umamax-scraper",
            description="うままっくす スクレイピング（umamax.com / 毎晩21時に翌日分取得）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "AI_PREDICTIONS_TABLE_NAME": ai_predictions_table.table_name,
            },
        )
        ai_predictions_table.grant_write_data(umamax_scraper_fn)

        # 無料競馬AI スクレイピング Lambda
        muryou_scraper_fn = lambda_.Function(
            self,
            "MuryouKeibaAiScraperFunction",
            handler="batch.muryou_keiba_ai_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-muryou-keiba-ai-scraper",
            description="無料競馬AI予想スクレイピング（muryou-keiba-ai.jp）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "AI_PREDICTIONS_TABLE_NAME": ai_predictions_table.table_name,
            },
        )
        ai_predictions_table.grant_write_data(muryou_scraper_fn)

        # ========================================
        # スピード指数スクレイパー Lambda
        # ========================================

        # 競馬新聞＆スピード指数 スクレイパー
        jiro8_scraper_fn = lambda_.Function(
            self,
            "Jiro8SpeedIndexScraperFunction",
            handler="batch.jiro8_speed_index_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-jiro8-speed-index-scraper",
            description="競馬新聞＆スピード指数スクレイピング（jiro8.sakura.ne.jp / 土日朝）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "SPEED_INDICES_TABLE_NAME": speed_indices_table.table_name,
            },
        )
        speed_indices_table.grant_write_data(jiro8_scraper_fn)

        # 吉馬 スクレイパー
        kichiuma_scraper_fn = lambda_.Function(
            self,
            "KichiumaScraperFunction",
            handler="batch.kichiuma_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-kichiuma-scraper",
            description="吉馬スクレイピング（kichiuma.net / 土日朝）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "SPEED_INDICES_TABLE_NAME": speed_indices_table.table_name,
            },
        )
        speed_indices_table.grant_write_data(kichiuma_scraper_fn)

        # デイリースポーツ スピード指数 スクレイパー
        daily_speed_scraper_fn = lambda_.Function(
            self,
            "DailySpeedIndexScraperFunction",
            handler="batch.daily_speed_index_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-daily-speed-index-scraper",
            description="デイリースポーツ スピード指数スクレイピング（daily.co.jp / 水曜18時）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "SPEED_INDICES_TABLE_NAME": speed_indices_table.table_name,
            },
        )
        speed_indices_table.grant_write_data(daily_speed_scraper_fn)

        # ========================================
        # 馬柱スクレイパー Lambda
        # ========================================

        # 競馬グラント スクレイパー
        keibagrant_scraper_fn = lambda_.Function(
            self,
            "KeibagrantScraperFunction",
            handler="batch.keibagrant_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-keibagrant-scraper",
            description="競馬グラント 馬柱スクレイピング（keibagrant.jp / 土日朝）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "PAST_PERFORMANCES_TABLE_NAME": past_performances_table.table_name,
            },
        )
        past_performances_table.grant_write_data(keibagrant_scraper_fn)

        # ========================================
        # EventBridge ルール（AI予想スクレイパー）
        # ========================================

        # AI指数・夜（毎晩 21:00 JST = 12:00 UTC、翌日分を前日取得）
        # construct IDは既存リソースとの互換性のため "AiShisuScraperRule" を維持
        ai_shisu_evening_rule = events.Rule(
            self,
            "AiShisuScraperRule",
            rule_name="baken-kaigi-ai-shisu-scraper-rule",
            description="AI指数スクレイピングを毎晩21:00 JSTに実行（翌日分を前日取得）",
            schedule=events.Schedule.cron(
                minute="0",
                hour="12",
                month="*",
                week_day="*",
                year="*",
            ),
        )
        ai_shisu_evening_rule.add_target(
            targets.LambdaFunction(
                ai_shisu_scraper_fn,
                event=events.RuleTargetInput.from_object({"offset_days": 1}),
            )
        )

        # AI指数・朝（毎朝 9:00 JST = 0:00 UTC、当日分を再取得）
        ai_shisu_morning_rule = events.Rule(
            self,
            "AiShisuScraperMorningRule",
            rule_name="baken-kaigi-ai-shisu-scraper-morning-rule",
            description="AI指数スクレイピングを毎朝9:00 JSTに実行（当日分を再取得）",
            schedule=events.Schedule.cron(
                minute="0",
                hour="0",
                month="*",
                week_day="*",
                year="*",
            ),
        )
        ai_shisu_morning_rule.add_target(
            targets.LambdaFunction(
                ai_shisu_scraper_fn,
                event=events.RuleTargetInput.from_object({"offset_days": 0}),
            )
        )

        # 競馬AI ATHENA（毎晩 21:10 JST = 12:10 UTC）
        keiba_ai_athena_rule = events.Rule(
            self,
            "KeibaAiAthenaScraperRule",
            rule_name="baken-kaigi-keiba-ai-athena-scraper-rule",
            description="競馬AI ATHENAスクレイピングを毎晩21:10 JSTに実行",
            schedule=events.Schedule.cron(
                minute="10",
                hour="12",
                month="*",
                week_day="*",
                year="*",
            ),
        )
        keiba_ai_athena_rule.add_target(targets.LambdaFunction(keiba_ai_athena_scraper_fn))

        # 競馬AIナビ（毎晩 21:20 JST = 12:20 UTC）
        keiba_ai_navi_rule = events.Rule(
            self,
            "KeibaAiNaviScraperRule",
            rule_name="baken-kaigi-keiba-ai-navi-scraper-rule",
            description="競馬AIナビスクレイピングを毎晩21:20 JSTに実行",
            schedule=events.Schedule.cron(
                minute="20",
                hour="12",
                month="*",
                week_day="*",
                year="*",
            ),
        )
        keiba_ai_navi_rule.add_target(targets.LambdaFunction(keiba_ai_navi_scraper_fn))

        # うままっくす（毎晩 21:30 JST = 12:30 UTC）
        umamax_rule = events.Rule(
            self,
            "UmamaxScraperRule",
            rule_name="baken-kaigi-umamax-scraper-rule",
            description="うままっくすスクレイピングを毎晩21:30 JSTに実行",
            schedule=events.Schedule.cron(
                minute="30",
                hour="12",
                month="*",
                week_day="*",
                year="*",
            ),
        )
        umamax_rule.add_target(targets.LambdaFunction(umamax_scraper_fn))

        # 無料競馬AI（当日朝 9:30 JST = 0:30 UTC）
        muryou_morning_rule = events.Rule(
            self,
            "MuryouScraperMorningRule",
            rule_name="baken-kaigi-muryou-keiba-ai-scraper-morning-rule",
            description="無料競馬AI予想を当日朝9:30 JSTに取得（最終更新版）",
            schedule=events.Schedule.cron(
                minute="30",
                hour="0",
                month="*",
                week_day="*",
                year="*",
            ),
        )
        muryou_morning_rule.add_target(
            targets.LambdaFunction(
                muryou_scraper_fn,
                event=events.RuleTargetInput.from_object({"offset_days": 0}),
            )
        )

        # 無料競馬AI（前日夜 21:00 JST = 12:00 UTC）
        muryou_evening_rule = events.Rule(
            self,
            "MuryouScraperEveningRule",
            rule_name="baken-kaigi-muryou-keiba-ai-scraper-evening-rule",
            description="無料競馬AI予想を前日21:00 JSTに早期取得（翌日分）",
            schedule=events.Schedule.cron(
                minute="0",
                hour="12",
                month="*",
                week_day="*",
                year="*",
            ),
        )
        muryou_evening_rule.add_target(
            targets.LambdaFunction(
                muryou_scraper_fn,
                event=events.RuleTargetInput.from_object({"offset_days": 1}),
            )
        )

        # ========================================
        # EventBridge ルール（スピード指数スクレイパー）
        # ========================================

        # 競馬新聞＆スピード指数（土日 6:00 JST = 金土 21:00 UTC）
        jiro8_rule = events.Rule(
            self,
            "Jiro8ScraperRule",
            rule_name="baken-kaigi-jiro8-speed-index-scraper-rule",
            description="競馬新聞＆スピード指数スクレイピングを土日6:00 JSTに実行",
            schedule=events.Schedule.cron(
                minute="0",
                hour="21",
                month="*",
                week_day="FRI,SAT",
                year="*",
            ),
        )
        jiro8_rule.add_target(targets.LambdaFunction(jiro8_scraper_fn))

        # 吉馬（土日 6:10 JST = 金土 21:10 UTC）
        kichiuma_rule = events.Rule(
            self,
            "KichiumaScraperRule",
            rule_name="baken-kaigi-kichiuma-scraper-rule",
            description="吉馬スクレイピングを土日6:10 JSTに実行",
            schedule=events.Schedule.cron(
                minute="10",
                hour="21",
                month="*",
                week_day="FRI,SAT",
                year="*",
            ),
        )
        kichiuma_rule.add_target(targets.LambdaFunction(kichiuma_scraper_fn))

        # デイリースポーツ（水曜 18:00 JST = 水曜 9:00 UTC）
        daily_speed_rule = events.Rule(
            self,
            "DailySpeedIndexScraperRule",
            rule_name="baken-kaigi-daily-speed-index-scraper-rule",
            description="デイリースポーツ スピード指数スクレイピングを水曜18:00 JSTに実行",
            schedule=events.Schedule.cron(
                minute="0",
                hour="9",
                month="*",
                week_day="WED",
                year="*",
            ),
        )
        daily_speed_rule.add_target(targets.LambdaFunction(daily_speed_scraper_fn))

        # ========================================
        # EventBridge ルール（馬柱スクレイパー）
        # ========================================

        # 競馬グラント（土日 6:20 JST = 金土 21:20 UTC）
        keibagrant_rule = events.Rule(
            self,
            "KeibagrantScraperRule",
            rule_name="baken-kaigi-keibagrant-scraper-rule",
            description="競馬グラント馬柱スクレイピングを土日6:20 JSTに実行",
            schedule=events.Schedule.cron(
                minute="20",
                hour="21",
                month="*",
                week_day="FRI,SAT",
                year="*",
            ),
        )
        keibagrant_rule.add_target(targets.LambdaFunction(keibagrant_scraper_fn))

        # ========================================
        # JRAチェックサム自動更新バッチ
        # ========================================

        jra_checksum_updater_props: dict = {
            "runtime": lambda_.Runtime.PYTHON_3_12,
            "timeout": Duration.seconds(300),
            "memory_size": 256,
            "layers": [batch_deps_layer],
            "environment": {
                "PYTHONPATH": "/var/task:/opt/python",
            },
        }

        # VPC設定（EC2にアクセスするためVPC内に配置）
        if vpc is not None:
            jra_checksum_updater_props["vpc"] = vpc
            jra_checksum_updater_props["vpc_subnets"] = ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )

        if use_jravan and jravan_api_url is not None:
            jra_checksum_updater_props["environment"]["JRAVAN_API_URL"] = jravan_api_url

        jra_checksum_updater_fn = lambda_.Function(
            self,
            "JraChecksumUpdaterFunction",
            handler="batch.jra_checksum_updater.handler",
            code=backend_code,
            function_name="baken-kaigi-jra-checksum-updater",
            description="JRA出馬表チェックサム自動更新",
            **jra_checksum_updater_props,
        )

        # EventBridge ルール（毎朝 6:10 JST = 21:10 UTC 前日）
        checksum_rule = events.Rule(
            self,
            "JraChecksumUpdaterRule",
            rule_name="baken-kaigi-jra-checksum-updater-rule",
            description="JRAチェックサム自動更新を毎朝6:10 JSTに実行",
            schedule=events.Schedule.cron(
                minute="10",
                hour="21",
                month="*",
                week_day="*",
                year="*",
            ),
        )
        checksum_rule.add_target(targets.LambdaFunction(jra_checksum_updater_fn))
