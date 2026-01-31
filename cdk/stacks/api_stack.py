"""馬券会議 API スタック."""
from pathlib import Path

from aws_cdk import BundlingOptions, CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from constructs import Construct


class BakenKaigiApiStack(Stack):
    """馬券会議 API スタック.

    Lambda + API Gateway + DynamoDB でサーバーレス API を構築する。
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc | None = None,
        jravan_api_url: str | None = None,
        allow_dev_origins: bool = False,
        **kwargs,
    ) -> None:
        """スタックを初期化する.

        Args:
            scope: CDK スコープ
            construct_id: コンストラクト ID
            vpc: VPC（JRA-VAN 連携時に必要）
            jravan_api_url: JRA-VAN API の URL（例: http://10.0.1.100:8000）
            allow_dev_origins: 開発用オリジン（localhost）を許可するかどうか
            **kwargs: その他のスタックパラメータ
        """
        super().__init__(scope, construct_id, **kwargs)

        # プロジェクトルートディレクトリ
        project_root = Path(__file__).parent.parent.parent

        # JRA-VAN 連携設定
        use_jravan = jravan_api_url is not None

        # ========================================
        # DynamoDB テーブル
        # ========================================

        # Cart テーブル
        cart_table = dynamodb.Table(
            self,
            "CartTable",
            table_name="baken-kaigi-cart",
            partition_key=dynamodb.Attribute(
                name="cart_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # 開発環境用
            time_to_live_attribute="ttl",
        )
        # user_id での検索用 GSI
        cart_table.add_global_secondary_index(
            index_name="user_id-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        # ConsultationSession テーブル
        session_table = dynamodb.Table(
            self,
            "ConsultationSessionTable",
            table_name="baken-kaigi-consultation-session",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # 開発環境用
            time_to_live_attribute="ttl",
        )
        # user_id での検索用 GSI
        session_table.add_global_secondary_index(
            index_name="user_id-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        # AI予想データテーブル
        ai_predictions_table = dynamodb.Table(
            self,
            "AiPredictionsTable",
            table_name="baken-kaigi-ai-predictions",
            partition_key=dynamodb.Attribute(
                name="race_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="source",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # 開発環境用
            time_to_live_attribute="ttl",
        )

        # ========================================
        # Lambda Layer（デプロイ時に自動で依存関係をインストール）
        # ========================================
        lambda_layer_path = project_root / "cdk" / "lambda_layer"
        deps_layer = lambda_.LayerVersion(
            self,
            "DepsLayer",
            code=lambda_.Code.from_asset(
                str(lambda_layer_path),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output/python",
                    ],
                ),
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Dependencies layer for baken-kaigi",
        )

        # 共通Lambda設定
        lambda_environment = {
            "PYTHONPATH": "/var/task:/opt/python",
            "CART_TABLE_NAME": cart_table.table_name,
            "SESSION_TABLE_NAME": session_table.table_name,
            "AI_PREDICTIONS_TABLE_NAME": ai_predictions_table.table_name,
            "CODE_VERSION": "5",  # コード更新強制用
        }

        # JRA-VAN 連携時の環境変数を追加
        if use_jravan:
            lambda_environment["RACE_DATA_PROVIDER"] = "jravan"
            lambda_environment["JRAVAN_API_URL"] = jravan_api_url  # type: ignore

        lambda_common_props: dict = {
            "runtime": lambda_.Runtime.PYTHON_3_12,
            "timeout": Duration.seconds(30),
            "memory_size": 256,
            "layers": [deps_layer],
            "environment": lambda_environment,
        }

        # VPC 設定（JRA-VAN 連携時に必要）
        # Lambda はプライベート（ISOLATED）サブネットに配置
        # DynamoDB へは VPC Gateway Endpoint 経由でアクセス
        # EC2 へは VPC 内通信でアクセス
        if vpc is not None:
            lambda_common_props["vpc"] = vpc
            lambda_common_props["vpc_subnets"] = ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )

        # Lambda関数を作成
        # レースAPI
        get_races_fn = lambda_.Function(
            self,
            "GetRacesFunction",
            handler="src.api.handlers.races.get_races",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-races",
            description="レース一覧取得",
            **lambda_common_props,
        )

        get_race_detail_fn = lambda_.Function(
            self,
            "GetRaceDetailFunction",
            handler="src.api.handlers.races.get_race_detail",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-race-detail",
            description="レース詳細取得",
            **lambda_common_props,
        )

        get_race_dates_fn = lambda_.Function(
            self,
            "GetRaceDatesFunction",
            handler="src.api.handlers.races.get_race_dates",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-race-dates",
            description="開催日一覧取得",
            **lambda_common_props,
        )

        get_odds_history_fn = lambda_.Function(
            self,
            "GetOddsHistoryFunction",
            handler="src.api.handlers.races.get_odds_history",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-odds-history",
            description="オッズ履歴取得",
            **lambda_common_props,
        )

        # カートAPI
        add_to_cart_fn = lambda_.Function(
            self,
            "AddToCartFunction",
            handler="src.api.handlers.cart.add_to_cart",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-add-to-cart",
            description="カートに買い目追加",
            **lambda_common_props,
        )

        get_cart_fn = lambda_.Function(
            self,
            "GetCartFunction",
            handler="src.api.handlers.cart.get_cart",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-cart",
            description="カート取得",
            **lambda_common_props,
        )

        remove_from_cart_fn = lambda_.Function(
            self,
            "RemoveFromCartFunction",
            handler="src.api.handlers.cart.remove_from_cart",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-remove-from-cart",
            description="カートアイテム削除",
            **lambda_common_props,
        )

        clear_cart_fn = lambda_.Function(
            self,
            "ClearCartFunction",
            handler="src.api.handlers.cart.clear_cart",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-clear-cart",
            description="カートクリア",
            **lambda_common_props,
        )

        # 相談API
        start_consultation_fn = lambda_.Function(
            self,
            "StartConsultationFunction",
            handler="src.api.handlers.consultation.start_consultation",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-start-consultation",
            description="AI相談開始",
            **lambda_common_props,
        )

        send_message_fn = lambda_.Function(
            self,
            "SendMessageFunction",
            handler="src.api.handlers.consultation.send_message",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-send-message",
            description="メッセージ送信",
            **lambda_common_props,
        )

        get_consultation_fn = lambda_.Function(
            self,
            "GetConsultationFunction",
            handler="src.api.handlers.consultation.get_consultation",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-consultation",
            description="相談セッション取得",
            **lambda_common_props,
        )

        # 馬API
        get_horse_performances_fn = lambda_.Function(
            self,
            "GetHorsePerformancesFunction",
            handler="src.api.handlers.horses.get_horse_performances",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-horse-performances",
            description="馬の過去成績取得",
            **lambda_common_props,
        )

        get_horse_training_fn = lambda_.Function(
            self,
            "GetHorseTrainingFunction",
            handler="src.api.handlers.horses.get_horse_training",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-horse-training",
            description="馬の調教データ取得",
            **lambda_common_props,
        )

        get_extended_pedigree_fn = lambda_.Function(
            self,
            "GetExtendedPedigreeFunction",
            handler="src.api.handlers.horses.get_extended_pedigree",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-extended-pedigree",
            description="馬の拡張血統情報取得",
            **lambda_common_props,
        )

        get_course_aptitude_fn = lambda_.Function(
            self,
            "GetCourseAptitudeFunction",
            handler="src.api.handlers.horses.get_course_aptitude",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-course-aptitude",
            description="馬のコース適性取得",
            **lambda_common_props,
        )

        # 騎手API
        get_jockey_info_fn = lambda_.Function(
            self,
            "GetJockeyInfoFunction",
            handler="src.api.handlers.jockeys.get_jockey_info",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-jockey-info",
            description="騎手基本情報取得",
            **lambda_common_props,
        )

        get_jockey_stats_fn = lambda_.Function(
            self,
            "GetJockeyStatsFunction",
            handler="src.api.handlers.jockeys.get_jockey_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-jockey-stats",
            description="騎手成績統計取得",
            **lambda_common_props,
        )

        # 厩舎API
        get_trainer_info_fn = lambda_.Function(
            self,
            "GetTrainerInfoFunction",
            handler="src.api.handlers.trainers.get_trainer_info",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-trainer-info",
            description="厩舎基本情報取得",
            **lambda_common_props,
        )

        get_trainer_stats_fn = lambda_.Function(
            self,
            "GetTrainerStatsFunction",
            handler="src.api.handlers.trainers.get_trainer_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-trainer-stats",
            description="厩舎成績統計取得",
            **lambda_common_props,
        )

        # 種牡馬API
        get_stallion_offspring_stats_fn = lambda_.Function(
            self,
            "GetStallionOffspringStatsFunction",
            handler="src.api.handlers.stallions.get_stallion_offspring_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-stallion-offspring-stats",
            description="種牡馬産駒成績統計取得",
            **lambda_common_props,
        )

        # レース結果API
        get_race_results_fn = lambda_.Function(
            self,
            "GetRaceResultsFunction",
            handler="src.api.handlers.races.get_race_results",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-race-results",
            description="レース結果・払戻取得",
            **lambda_common_props,
        )

        # 馬主API
        get_owner_info_fn = lambda_.Function(
            self,
            "GetOwnerInfoFunction",
            handler="src.api.handlers.owners.get_owner_info",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-owner-info",
            description="馬主基本情報取得",
            **lambda_common_props,
        )

        get_owner_stats_fn = lambda_.Function(
            self,
            "GetOwnerStatsFunction",
            handler="src.api.handlers.owners.get_owner_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-owner-stats",
            description="馬主成績統計取得",
            **lambda_common_props,
        )

        # 生産者API
        get_breeder_info_fn = lambda_.Function(
            self,
            "GetBreederInfoFunction",
            handler="src.api.handlers.owners.get_breeder_info",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-breeder-info",
            description="生産者基本情報取得",
            **lambda_common_props,
        )

        get_breeder_stats_fn = lambda_.Function(
            self,
            "GetBreederStatsFunction",
            handler="src.api.handlers.owners.get_breeder_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-breeder-stats",
            description="生産者成績統計取得",
            **lambda_common_props,
        )

        # 統計API
        get_gate_position_stats_fn = lambda_.Function(
            self,
            "GetGatePositionStatsFunction",
            handler="src.api.handlers.statistics.get_gate_position_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-gate-position-stats",
            description="枠順別成績統計取得",
            **lambda_common_props,
        )

        get_past_race_stats_fn = lambda_.Function(
            self,
            "GetPastRaceStatsFunction",
            handler="src.api.handlers.statistics.get_past_race_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-past-race-stats",
            description="過去レース統計取得",
            **lambda_common_props,
        )

        get_jockey_course_stats_fn = lambda_.Function(
            self,
            "GetJockeyCourseStatsFunction",
            handler="src.api.handlers.statistics.get_jockey_course_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-jockey-course-stats",
            description="騎手コース別成績取得",
            **lambda_common_props,
        )

        get_popularity_payout_stats_fn = lambda_.Function(
            self,
            "GetPopularityPayoutStatsFunction",
            handler="src.api.handlers.statistics.get_popularity_payout_stats",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-popularity-payout-stats",
            description="人気別配当統計取得",
            **lambda_common_props,
        )

        # API Gateway
        # CORS設定: 本番環境は特定オリジンのみ許可
        # --context allow_dev_origins=true で開発用オリジンも許可
        cors_origins = [
            "https://bakenkaigi.com",
            "https://www.bakenkaigi.com",
        ]
        if allow_dev_origins:
            cors_origins.extend([
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
            ])

        api = apigw.RestApi(
            self,
            "BakenKaigiApi",
            rest_api_name="baken-kaigi-api",
            description="馬券会議 API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=cors_origins,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "x-api-key"],
            ),
        )

        # ========================================
        # API Key 認証
        # ========================================

        # 本番用 API Key
        api_key_prod = apigw.ApiKey(
            self,
            "BakenKaigiApiKeyProd",
            api_key_name="baken-kaigi-api-key-prod",
            description="馬券会議 API Key (本番環境)",
        )

        # 開発用 API Key
        api_key_dev = apigw.ApiKey(
            self,
            "BakenKaigiApiKeyDev",
            api_key_name="baken-kaigi-api-key-dev",
            description="馬券会議 API Key (開発環境)",
        )

        # Usage Plan（レート制限）
        usage_plan = apigw.UsagePlan(
            self,
            "BakenKaigiUsagePlan",
            name="baken-kaigi-usage-plan",
            description="馬券会議 API 利用プラン",
            throttle=apigw.ThrottleSettings(
                rate_limit=100,  # 1秒あたり100リクエスト
                burst_limit=200,  # バースト時200リクエスト
            ),
            quota=apigw.QuotaSettings(
                limit=10000,  # 1日あたり10000リクエスト
                period=apigw.Period.DAY,
            ),
        )

        # API Key を Usage Plan に紐付け
        usage_plan.add_api_key(api_key_prod)
        usage_plan.add_api_key(api_key_dev)

        # Usage Plan に API ステージを紐付け
        usage_plan.add_api_stage(stage=api.deployment_stage)

        # エンドポイント定義
        # /race-dates
        race_dates = api.root.add_resource("race-dates")
        race_dates.add_method(
            "GET", apigw.LambdaIntegration(get_race_dates_fn), api_key_required=True
        )

        # /races
        races = api.root.add_resource("races")
        races.add_method(
            "GET", apigw.LambdaIntegration(get_races_fn), api_key_required=True
        )

        # /races/{race_id}
        race = races.add_resource("{race_id}")
        race.add_method(
            "GET", apigw.LambdaIntegration(get_race_detail_fn), api_key_required=True
        )

        # /races/{race_id}/odds-history
        race_odds_history = race.add_resource("odds-history")
        race_odds_history.add_method(
            "GET", apigw.LambdaIntegration(get_odds_history_fn), api_key_required=True
        )

        # /races/{race_id}/results
        race_results = race.add_resource("results")
        race_results.add_method(
            "GET", apigw.LambdaIntegration(get_race_results_fn), api_key_required=True
        )

        # /horses
        horses = api.root.add_resource("horses")

        # /horses/{horse_id}
        horse = horses.add_resource("{horse_id}")

        # /horses/{horse_id}/performances
        horse_performances = horse.add_resource("performances")
        horse_performances.add_method(
            "GET", apigw.LambdaIntegration(get_horse_performances_fn), api_key_required=True
        )

        # /horses/{horse_id}/training
        horse_training = horse.add_resource("training")
        horse_training.add_method(
            "GET", apigw.LambdaIntegration(get_horse_training_fn), api_key_required=True
        )

        # /horses/{horse_id}/pedigree/extended
        horse_pedigree = horse.add_resource("pedigree")
        horse_pedigree_extended = horse_pedigree.add_resource("extended")
        horse_pedigree_extended.add_method(
            "GET", apigw.LambdaIntegration(get_extended_pedigree_fn), api_key_required=True
        )

        # /horses/{horse_id}/course-aptitude
        horse_course_aptitude = horse.add_resource("course-aptitude")
        horse_course_aptitude.add_method(
            "GET", apigw.LambdaIntegration(get_course_aptitude_fn), api_key_required=True
        )

        # /jockeys
        jockeys = api.root.add_resource("jockeys")

        # /jockeys/{jockey_id}
        jockey = jockeys.add_resource("{jockey_id}")

        # /jockeys/{jockey_id}/info
        jockey_info = jockey.add_resource("info")
        jockey_info.add_method(
            "GET", apigw.LambdaIntegration(get_jockey_info_fn), api_key_required=True
        )

        # /jockeys/{jockey_id}/stats
        jockey_stats = jockey.add_resource("stats")
        jockey_stats.add_method(
            "GET", apigw.LambdaIntegration(get_jockey_stats_fn), api_key_required=True
        )

        # /trainers
        trainers = api.root.add_resource("trainers")

        # /trainers/{trainer_id}
        trainer = trainers.add_resource("{trainer_id}")

        # /trainers/{trainer_id}/info
        trainer_info = trainer.add_resource("info")
        trainer_info.add_method(
            "GET", apigw.LambdaIntegration(get_trainer_info_fn), api_key_required=True
        )

        # /trainers/{trainer_id}/stats
        trainer_stats = trainer.add_resource("stats")
        trainer_stats.add_method(
            "GET", apigw.LambdaIntegration(get_trainer_stats_fn), api_key_required=True
        )

        # /stallions
        stallions = api.root.add_resource("stallions")

        # /stallions/{stallion_id}
        stallion = stallions.add_resource("{stallion_id}")

        # /stallions/{stallion_id}/offspring-stats
        stallion_offspring_stats = stallion.add_resource("offspring-stats")
        stallion_offspring_stats.add_method(
            "GET", apigw.LambdaIntegration(get_stallion_offspring_stats_fn), api_key_required=True
        )

        # /owners
        owners = api.root.add_resource("owners")

        # /owners/{owner_id}
        owner = owners.add_resource("{owner_id}")
        owner.add_method(
            "GET", apigw.LambdaIntegration(get_owner_info_fn), api_key_required=True
        )

        # /owners/{owner_id}/stats
        owner_stats = owner.add_resource("stats")
        owner_stats.add_method(
            "GET", apigw.LambdaIntegration(get_owner_stats_fn), api_key_required=True
        )

        # /breeders
        breeders = api.root.add_resource("breeders")

        # /breeders/{breeder_id}
        breeder = breeders.add_resource("{breeder_id}")
        breeder.add_method(
            "GET", apigw.LambdaIntegration(get_breeder_info_fn), api_key_required=True
        )

        # /breeders/{breeder_id}/stats
        breeder_stats = breeder.add_resource("stats")
        breeder_stats.add_method(
            "GET", apigw.LambdaIntegration(get_breeder_stats_fn), api_key_required=True
        )

        # /statistics
        statistics = api.root.add_resource("statistics")

        # /statistics/gate-position
        gate_position_stats = statistics.add_resource("gate-position")
        gate_position_stats.add_method(
            "GET", apigw.LambdaIntegration(get_gate_position_stats_fn), api_key_required=True
        )

        # /statistics/past-races
        past_race_stats = statistics.add_resource("past-races")
        past_race_stats.add_method(
            "GET", apigw.LambdaIntegration(get_past_race_stats_fn), api_key_required=True
        )

        # /statistics/jockey-course
        jockey_course_stats = statistics.add_resource("jockey-course")
        jockey_course_stats.add_method(
            "GET", apigw.LambdaIntegration(get_jockey_course_stats_fn), api_key_required=True
        )

        # /statistics/popularity-payout
        popularity_payout_stats = statistics.add_resource("popularity-payout")
        popularity_payout_stats.add_method(
            "GET", apigw.LambdaIntegration(get_popularity_payout_stats_fn), api_key_required=True
        )

        # /cart
        cart = api.root.add_resource("cart")

        # /cart/items
        cart_items = cart.add_resource("items")
        cart_items.add_method(
            "POST", apigw.LambdaIntegration(add_to_cart_fn), api_key_required=True
        )

        # /cart/{cart_id}
        cart_by_id = cart.add_resource("{cart_id}")
        cart_by_id.add_method(
            "GET", apigw.LambdaIntegration(get_cart_fn), api_key_required=True
        )
        cart_by_id.add_method(
            "DELETE", apigw.LambdaIntegration(clear_cart_fn), api_key_required=True
        )

        # /cart/{cart_id}/items/{item_id}
        cart_items_by_id = cart_by_id.add_resource("items").add_resource("{item_id}")
        cart_items_by_id.add_method(
            "DELETE", apigw.LambdaIntegration(remove_from_cart_fn), api_key_required=True
        )

        # /consultations
        consultations = api.root.add_resource("consultations")
        consultations.add_method(
            "POST", apigw.LambdaIntegration(start_consultation_fn), api_key_required=True
        )

        # /consultations/{session_id}
        consultation = consultations.add_resource("{session_id}")
        consultation.add_method(
            "GET", apigw.LambdaIntegration(get_consultation_fn), api_key_required=True
        )

        # /consultations/{session_id}/messages
        messages = consultation.add_resource("messages")
        messages.add_method(
            "POST", apigw.LambdaIntegration(send_message_fn), api_key_required=True
        )

        # ========================================
        # AgentCore 相談 API
        # ========================================
        agentcore_consultation_fn = lambda_.Function(
            self,
            "AgentCoreConsultationFunction",
            handler="agentcore_handler.invoke_agentcore",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-agentcore-consultation",
            description="AgentCore AI 相談",
            timeout=Duration.seconds(60),  # AgentCore は時間がかかる場合がある
            memory_size=256,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "AGENTCORE_AGENT_ARN": "arn:aws:bedrock-agentcore:ap-northeast-1:688567287706:runtime/baken_kaigi_ai-dfTUpICY2G",
            },
        )

        # AgentCore Runtime への呼び出し権限
        agentcore_consultation_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeAgent",
                    "bedrock-agentcore:InvokeAgent",
                    "bedrock-agentcore:Invoke",
                ],
                resources=["*"],  # AgentCore ARN を指定
            )
        )

        # /api/consultation
        api_resource = api.root.add_resource("api")
        consultation_resource = api_resource.add_resource("consultation")
        consultation_resource.add_method(
            "POST",
            apigw.LambdaIntegration(agentcore_consultation_fn),
            api_key_required=True,
        )

        # ========================================
        # AI予想スクレイピングバッチ
        # ========================================

        # スクレイピングバッチ用 Lambda Layer
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

        # AI指数スクレイピング Lambda
        ai_shisu_scraper_fn = lambda_.Function(
            self,
            "AiShisuScraperFunction",
            handler="batch.ai_shisu_scraper.handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-ai-shisu-scraper",
            description="AI指数スクレイピング（ai-shisu.com）",
            timeout=Duration.seconds(300),  # スクレイピングは時間がかかる
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "AI_PREDICTIONS_TABLE_NAME": ai_predictions_table.table_name,
            },
        )

        # AI指数スクレイピング Lambda に DynamoDB 書き込み権限を付与
        ai_predictions_table.grant_write_data(ai_shisu_scraper_fn)

        # EventBridge ルール（毎朝 6:00 JST = 21:00 UTC 前日）
        scraper_rule = events.Rule(
            self,
            "AiShisuScraperRule",
            rule_name="baken-kaigi-ai-shisu-scraper-rule",
            description="AI指数スクレイピングを毎朝6:00 JSTに実行",
            schedule=events.Schedule.cron(
                minute="0",
                hour="21",  # UTC 21:00 = JST 06:00
                month="*",
                week_day="*",
                year="*",
            ),
        )
        scraper_rule.add_target(targets.LambdaFunction(ai_shisu_scraper_fn))

        # ========================================
        # DynamoDB アクセス権限
        # ========================================

        # カート関連 Lambda に Cart テーブルへのアクセス権限を付与
        cart_functions = [add_to_cart_fn, get_cart_fn, remove_from_cart_fn, clear_cart_fn]
        for fn in cart_functions:
            cart_table.grant_read_write_data(fn)

        # 相談関連 Lambda に両テーブルへのアクセス権限を付与
        # （相談開始時にカートを参照するため）
        consultation_functions = [start_consultation_fn, send_message_fn, get_consultation_fn]
        for fn in consultation_functions:
            cart_table.grant_read_data(fn)
            session_table.grant_read_write_data(fn)

        # ========================================
        # 出力
        # ========================================

        CfnOutput(
            self,
            "ApiKeyIdProd",
            value=api_key_prod.key_id,
            description="本番用 API Key ID（値の取得: aws apigateway get-api-key --api-key <ID> --include-value）",
        )

        CfnOutput(
            self,
            "ApiKeyIdDev",
            value=api_key_dev.key_id,
            description="開発用 API Key ID（値の取得: aws apigateway get-api-key --api-key <ID> --include-value）",
        )
