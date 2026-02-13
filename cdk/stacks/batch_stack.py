"""馬券会議 バッチ処理スタック.

スクレイパー Lambda + EventBridge ルールを管理する。
BakenKaigiApiStack から分離されたステートレスリソースのみ含む。
"""
from pathlib import Path

from aws_cdk import BundlingOptions, Duration, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
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
        **kwargs,
    ) -> None:
        """スタックを初期化する.

        Args:
            scope: CDK スコープ
            construct_id: コンストラクト ID
            **kwargs: その他のスタックパラメータ
        """
        super().__init__(scope, construct_id, **kwargs)

        project_root = Path(__file__).parent.parent.parent

        # ========================================
        # DynamoDB テーブル参照（既存テーブルを名前で参照）
        # ========================================
        ai_predictions_table = dynamodb.Table.from_table_name(
            self, "AiPredictionsTable", "baken-kaigi-ai-predictions"
        )
        speed_indices_table = dynamodb.Table.from_table_name(
            self, "SpeedIndicesTable", "baken-kaigi-speed-indices"
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

        # ========================================
        # HRDB-API バッチ Lambda
        # ========================================

        # HRDB用 DynamoDB テーブル参照
        hrdb_races_table = dynamodb.Table.from_table_name(
            self, "HrdbRacesTable", "baken-kaigi-races"
        )
        hrdb_runners_table = dynamodb.Table.from_table_name(
            self, "HrdbRunnersTable", "baken-kaigi-runners"
        )
        hrdb_horses_table = dynamodb.Table.from_table_name(
            self, "HrdbHorsesTable", "baken-kaigi-horses"
        )
        hrdb_jockeys_table = dynamodb.Table.from_table_name(
            self, "HrdbJockeysTable", "baken-kaigi-jockeys"
        )
        hrdb_trainers_table = dynamodb.Table.from_table_name(
            self, "HrdbTrainersTable", "baken-kaigi-trainers"
        )

        # Secrets Manager 読み取り権限用ポリシー
        gamble_os_secret_policy = iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:gamble-os-credentials*"
            ],
        )

        # HRDB共通環境変数
        hrdb_common_env = {
            "PYTHONPATH": "/var/task:/opt/python",
            "GAMBLE_OS_SECRET_ID": "gamble-os-credentials",
        }

        # --- HRDB レース取得 Lambda ---
        hrdb_races_scraper_fn = lambda_.Function(
            self,
            "HrdbRacesScraperFunction",
            handler="batch.hrdb_races_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-hrdb-races-scraper",
            description="HRDB-APIからレース情報を取得（毎晩21:00+当日朝8:00 JST）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                **hrdb_common_env,
                "RACES_TABLE_NAME": hrdb_races_table.table_name,
            },
        )
        hrdb_races_table.grant_write_data(hrdb_races_scraper_fn)
        hrdb_races_scraper_fn.add_to_role_policy(gamble_os_secret_policy)

        # --- HRDB 出走馬取得 Lambda ---
        hrdb_runners_scraper_fn = lambda_.Function(
            self,
            "HrdbRunnersScraperFunction",
            handler="batch.hrdb_runners_scraper.handler",
            code=backend_code,
            function_name="baken-kaigi-hrdb-runners-scraper",
            description="HRDB-APIから出走馬情報を取得（毎晩21:00+当日朝8:00 JST）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                **hrdb_common_env,
                "RUNNERS_TABLE_NAME": hrdb_runners_table.table_name,
            },
        )
        hrdb_runners_table.grant_write_data(hrdb_runners_scraper_fn)
        hrdb_runners_scraper_fn.add_to_role_policy(gamble_os_secret_policy)

        # --- HRDB 馬マスタ同期 Lambda ---
        hrdb_horses_sync_fn = lambda_.Function(
            self,
            "HrdbHorsesSyncFunction",
            handler="batch.hrdb_horses_sync.handler",
            code=backend_code,
            function_name="baken-kaigi-hrdb-horses-sync",
            description="HRDB-APIから馬マスタを差分同期（毎晩22:00 JST）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                **hrdb_common_env,
                "RUNNERS_TABLE_NAME": hrdb_runners_table.table_name,
                "HORSES_TABLE_NAME": hrdb_horses_table.table_name,
            },
        )
        hrdb_runners_table.grant_read_data(hrdb_horses_sync_fn)
        hrdb_horses_table.grant_read_write_data(hrdb_horses_sync_fn)
        hrdb_horses_sync_fn.add_to_role_policy(gamble_os_secret_policy)

        # --- HRDB 騎手マスタ同期 Lambda ---
        hrdb_jockeys_sync_fn = lambda_.Function(
            self,
            "HrdbJockeysSyncFunction",
            handler="batch.hrdb_jockeys_sync.handler",
            code=backend_code,
            function_name="baken-kaigi-hrdb-jockeys-sync",
            description="HRDB-APIから騎手マスタを差分同期（毎晩22:10 JST）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                **hrdb_common_env,
                "RUNNERS_TABLE_NAME": hrdb_runners_table.table_name,
                "JOCKEYS_TABLE_NAME": hrdb_jockeys_table.table_name,
            },
        )
        hrdb_runners_table.grant_read_data(hrdb_jockeys_sync_fn)
        hrdb_jockeys_table.grant_read_write_data(hrdb_jockeys_sync_fn)
        hrdb_jockeys_sync_fn.add_to_role_policy(gamble_os_secret_policy)

        # --- HRDB 調教師マスタ同期 Lambda ---
        hrdb_trainers_sync_fn = lambda_.Function(
            self,
            "HrdbTrainersSyncFunction",
            handler="batch.hrdb_trainers_sync.handler",
            code=backend_code,
            function_name="baken-kaigi-hrdb-trainers-sync",
            description="HRDB-APIから調教師マスタを差分同期（毎晩22:20 JST）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                **hrdb_common_env,
                "RUNNERS_TABLE_NAME": hrdb_runners_table.table_name,
                "TRAINERS_TABLE_NAME": hrdb_trainers_table.table_name,
            },
        )
        hrdb_runners_table.grant_read_data(hrdb_trainers_sync_fn)
        hrdb_trainers_table.grant_read_write_data(hrdb_trainers_sync_fn)
        hrdb_trainers_sync_fn.add_to_role_policy(gamble_os_secret_policy)

        # --- HRDB レース結果更新 Lambda ---
        hrdb_results_sync_fn = lambda_.Function(
            self,
            "HrdbResultsSyncFunction",
            handler="batch.hrdb_results_sync.handler",
            code=backend_code,
            function_name="baken-kaigi-hrdb-results-sync",
            description="HRDB-APIからレース結果を週次同期（毎週月曜6:00 JST）",
            timeout=Duration.seconds(300),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                **hrdb_common_env,
                "RUNNERS_TABLE_NAME": hrdb_runners_table.table_name,
            },
        )
        hrdb_runners_table.grant_write_data(hrdb_results_sync_fn)
        hrdb_results_sync_fn.add_to_role_policy(gamble_os_secret_policy)

        # ========================================
        # EventBridge ルール（HRDB バッチ）
        # ========================================

        # HRDB レース取得・夜（毎晩 21:00 JST = 12:00 UTC）
        hrdb_races_evening_rule = events.Rule(
            self,
            "HrdbRacesScraperEveningRule",
            rule_name="baken-kaigi-hrdb-races-scraper-evening-rule",
            description="HRDBレース取得を毎晩21:00 JSTに実行（翌日分）",
            schedule=events.Schedule.cron(
                minute="0", hour="12", month="*", week_day="*", year="*",
            ),
        )
        hrdb_races_evening_rule.add_target(
            targets.LambdaFunction(
                hrdb_races_scraper_fn,
                event=events.RuleTargetInput.from_object({"offset_days": 1}),
            )
        )

        # HRDB レース取得・朝（当日朝 8:00 JST = 23:00 UTC 前日）
        hrdb_races_morning_rule = events.Rule(
            self,
            "HrdbRacesScraperMorningRule",
            rule_name="baken-kaigi-hrdb-races-scraper-morning-rule",
            description="HRDBレース取得を当日朝8:00 JSTに実行（当日分再取得）",
            schedule=events.Schedule.cron(
                minute="0", hour="23", month="*", week_day="*", year="*",
            ),
        )
        hrdb_races_morning_rule.add_target(
            targets.LambdaFunction(
                hrdb_races_scraper_fn,
                event=events.RuleTargetInput.from_object({"offset_days": 0}),
            )
        )

        # HRDB 出走馬取得・夜（毎晩 21:05 JST = 12:05 UTC）
        hrdb_runners_evening_rule = events.Rule(
            self,
            "HrdbRunnersScraperEveningRule",
            rule_name="baken-kaigi-hrdb-runners-scraper-evening-rule",
            description="HRDB出走馬取得を毎晩21:05 JSTに実行（翌日分）",
            schedule=events.Schedule.cron(
                minute="5", hour="12", month="*", week_day="*", year="*",
            ),
        )
        hrdb_runners_evening_rule.add_target(
            targets.LambdaFunction(
                hrdb_runners_scraper_fn,
                event=events.RuleTargetInput.from_object({"offset_days": 1}),
            )
        )

        # HRDB 出走馬取得・朝（当日朝 8:05 JST = 23:05 UTC 前日）
        hrdb_runners_morning_rule = events.Rule(
            self,
            "HrdbRunnersScraperMorningRule",
            rule_name="baken-kaigi-hrdb-runners-scraper-morning-rule",
            description="HRDB出走馬取得を当日朝8:05 JSTに実行（当日分再取得）",
            schedule=events.Schedule.cron(
                minute="5", hour="23", month="*", week_day="*", year="*",
            ),
        )
        hrdb_runners_morning_rule.add_target(
            targets.LambdaFunction(
                hrdb_runners_scraper_fn,
                event=events.RuleTargetInput.from_object({"offset_days": 0}),
            )
        )

        # HRDB 馬マスタ同期（毎晩 22:00 JST = 13:00 UTC）
        hrdb_horses_sync_rule = events.Rule(
            self,
            "HrdbHorsesSyncRule",
            rule_name="baken-kaigi-hrdb-horses-sync-rule",
            description="HRDB馬マスタ同期を毎晩22:00 JSTに実行",
            schedule=events.Schedule.cron(
                minute="0", hour="13", month="*", week_day="*", year="*",
            ),
        )
        hrdb_horses_sync_rule.add_target(targets.LambdaFunction(hrdb_horses_sync_fn))

        # HRDB 騎手マスタ同期（毎晩 22:10 JST = 13:10 UTC）
        hrdb_jockeys_sync_rule = events.Rule(
            self,
            "HrdbJockeysSyncRule",
            rule_name="baken-kaigi-hrdb-jockeys-sync-rule",
            description="HRDB騎手マスタ同期を毎晩22:10 JSTに実行",
            schedule=events.Schedule.cron(
                minute="10", hour="13", month="*", week_day="*", year="*",
            ),
        )
        hrdb_jockeys_sync_rule.add_target(targets.LambdaFunction(hrdb_jockeys_sync_fn))

        # HRDB 調教師マスタ同期（毎晩 22:20 JST = 13:20 UTC）
        hrdb_trainers_sync_rule = events.Rule(
            self,
            "HrdbTrainersSyncRule",
            rule_name="baken-kaigi-hrdb-trainers-sync-rule",
            description="HRDB調教師マスタ同期を毎晩22:20 JSTに実行",
            schedule=events.Schedule.cron(
                minute="20", hour="13", month="*", week_day="*", year="*",
            ),
        )
        hrdb_trainers_sync_rule.add_target(targets.LambdaFunction(hrdb_trainers_sync_fn))

        # HRDB レース結果更新（毎週月曜 6:00 JST = 日曜 21:00 UTC）
        hrdb_results_sync_rule = events.Rule(
            self,
            "HrdbResultsSyncRule",
            rule_name="baken-kaigi-hrdb-results-sync-rule",
            description="HRDBレース結果更新を毎週月曜6:00 JSTに実行",
            schedule=events.Schedule.cron(
                minute="0", hour="21", month="*", week_day="SUN", year="*",
            ),
        )
        hrdb_results_sync_rule.add_target(targets.LambdaFunction(hrdb_results_sync_fn))
