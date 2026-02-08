"""馬券会議 API スタック."""
from pathlib import Path

from aws_cdk import BundlingOptions, CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_cognito as cognito
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

        # スピード指数テーブル
        speed_indices_table = dynamodb.Table(
            self,
            "SpeedIndicesTable",
            table_name="baken-kaigi-speed-indices",
            partition_key=dynamodb.Attribute(
                name="race_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="source",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

        # 馬柱（過去成績）テーブル
        past_performances_table = dynamodb.Table(
            self,
            "PastPerformancesTable",
            table_name="baken-kaigi-past-performances",
            partition_key=dynamodb.Attribute(
                name="race_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="source",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

        # ========================================
        # Cognito User Pool（ユーザー認証）
        # ========================================

        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name="baken-kaigi-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_lowercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                birthdate=cognito.StandardAttribute(required=False, mutable=True),
            ),
            custom_attributes={
                "display_name": cognito.StringAttribute(min_len=1, max_len=50, mutable=True),
                "terms_accepted_at": cognito.StringAttribute(min_len=1, max_len=100, mutable=True),
                "privacy_accepted_at": cognito.StringAttribute(min_len=1, max_len=100, mutable=True),
            },
            user_verification=cognito.UserVerificationConfig(
                email_subject="馬券会議 - メールアドレスの確認",
                email_body="馬券会議をご利用いただきありがとうございます。確認コード: {####}",
                email_style=cognito.VerificationEmailStyle.CODE,
            ),
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Google Identity Provider
        google_oauth_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "GoogleOAuthSecret",
            "baken-kaigi/google-oauth",
        )
        google_provider = cognito.UserPoolIdentityProviderGoogle(
            self,
            "GoogleProvider",
            user_pool=user_pool,
            client_id=google_oauth_secret.secret_value_from_json("client_id").unsafe_unwrap(),
            client_secret_value=google_oauth_secret.secret_value_from_json("client_secret"),
            scopes=["openid", "email", "profile"],
            attribute_mapping=cognito.AttributeMapping(
                email=cognito.ProviderAttribute.GOOGLE_EMAIL,
                fullname=cognito.ProviderAttribute.GOOGLE_NAME,
            ),
        )

        # User Pool Client（SPA用）
        user_pool_client = user_pool.add_client(
            "UserPoolClient",
            user_pool_client_name="baken-kaigi-spa-client",
            auth_flows=cognito.AuthFlow(
                user_srp=True,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                    cognito.OAuthScope.COGNITO_ADMIN,
                ],
                callback_urls=[
                    "https://bakenkaigi.com/auth/callback",
                    "http://localhost:5173/auth/callback",
                ],
                logout_urls=[
                    "https://bakenkaigi.com",
                    "http://localhost:5173",
                ],
            ),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO,
                cognito.UserPoolClientIdentityProvider.GOOGLE,
            ],
            access_token_validity=Duration.hours(8),
            id_token_validity=Duration.hours(8),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True,
        )
        user_pool_client.node.add_dependency(google_provider)

        # User Pool Domain
        user_pool_domain = user_pool.add_domain(
            "UserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"baken-kaigi-{Stack.of(self).account}",
            ),
        )

        # Cognito Authorizer
        cognito_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name="baken-kaigi-cognito-authorizer",
        )

        # User テーブル
        user_table = dynamodb.Table(
            self,
            "UserTable",
            table_name="baken-kaigi-user",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )
        # email での検索用 GSI
        user_table.add_global_secondary_index(
            index_name="email-index",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # LossLimitChange テーブル
        loss_limit_change_table = dynamodb.Table(
            self,
            "LossLimitChangeTable",
            table_name="baken-kaigi-loss-limit-change",
            partition_key=dynamodb.Attribute(
                name="change_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
        )
        # user_id での検索用 GSI
        loss_limit_change_table.add_global_secondary_index(
            index_name="user_id-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="requested_at",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        # Purchase Order テーブル
        purchase_order_table = dynamodb.Table(
            self,
            "PurchaseOrderTable",
            table_name="baken-kaigi-purchase-order",
            partition_key=dynamodb.Attribute(
                name="purchase_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        # user_id での検索用 GSI
        purchase_order_table.add_global_secondary_index(
            index_name="user_id-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        # Betting Record テーブル
        betting_record_table = dynamodb.Table(
            self,
            "BettingRecordTable",
            table_name="baken-kaigi-betting-record",
            partition_key=dynamodb.Attribute(
                name="record_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        # user_id + race_date での検索用 GSI
        betting_record_table.add_global_secondary_index(
            index_name="user_id-race_date-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="race_date",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        # ========================================
        # AgentCore Runtime
        # ========================================
        # NOTE: AgentCore RuntimeはCDKではなくagentcore CLIで管理
        # CLIでデプロイしたAgentはAWS側で依存関係のビルドが行われ、
        # 初期化タイムアウト問題を回避できる
        #
        # デプロイ手順:
        #   1. cd backend/agentcore
        #   2. agentcore deploy
        #   3. 出力されたAgent ARNからIDを取得（例: baken_kaigi_cli-V4Bt684fL5）
        #   4. CDKデプロイ時に --context agentcore_agent_id=<ID> を指定
        #      または .bedrock_agentcore.yaml の agent_id を確認
        #
        # Agent ID は CDK コンテキストから取得し、未設定の場合はデフォルト値を使用する
        agentcore_agent_id = self.node.try_get_context("agentcore_agent_id") or "baken_kaigi_cli-V4Bt684fL5"
        agentcore_agent_arn = (
            f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:runtime/{agentcore_agent_id}"
        )

        # AgentCore Runtime 実行ロール
        agentcore_runtime_role = iam.Role(
            self,
            "AgentCoreRuntimeRole",
            role_name="baken-kaigi-agentcore-runtime-role",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            description="IAM role for AgentCore Runtime",
        )

        # DynamoDB 読み取り権限
        ai_predictions_table.grant_read_data(agentcore_runtime_role)
        speed_indices_table.grant_read_data(agentcore_runtime_role)
        past_performances_table.grant_read_data(agentcore_runtime_role)

        # API Gateway - API Key 取得権限
        agentcore_runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["apigateway:GET"],
                resources=[f"arn:aws:apigateway:{self.region}::/apikeys/*"],
            )
        )

        # Bedrock InvokeModel 権限
        agentcore_runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{self.region}::foundation-model/*"],
            )
        )

        # CloudWatch Logs 権限
        agentcore_runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[f"arn:aws:logs:{self.region}:{self.account}:*"],
            )
        )

        # X-Ray トレーシング権限
        agentcore_runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

        # AgentCore Identity 権限
        agentcore_runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock-agentcore:GetToken",
                    "bedrock-agentcore:PutToken",
                ],
                resources=["*"],
            )
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
            "SPEED_INDICES_TABLE_NAME": speed_indices_table.table_name,
            "PAST_PERFORMANCES_TABLE_NAME": past_performances_table.table_name,
            "USER_TABLE_NAME": user_table.table_name,
            "PURCHASE_ORDER_TABLE_NAME": purchase_order_table.table_name,
            "BETTING_RECORD_TABLE_NAME": betting_record_table.table_name,
            "LOSS_LIMIT_CHANGE_TABLE_NAME": loss_limit_change_table.table_name,
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

        # ユーザーAPI
        get_user_profile_fn = lambda_.Function(
            self,
            "GetUserProfileFunction",
            handler="src.api.handlers.users.get_user_profile",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-user-profile",
            description="ユーザープロフィール取得",
            **lambda_common_props,
        )

        update_user_profile_fn = lambda_.Function(
            self,
            "UpdateUserProfileFunction",
            handler="src.api.handlers.users.update_user_profile",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-update-user-profile",
            description="ユーザープロフィール更新",
            **lambda_common_props,
        )

        delete_account_fn = lambda_.Function(
            self,
            "DeleteAccountFunction",
            handler="src.api.handlers.users.delete_account",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-delete-account",
            description="アカウント削除",
            **lambda_common_props,
        )

        # ========================================
        # 損失制限API
        # ========================================

        get_loss_limit_fn = lambda_.Function(
            self,
            "GetLossLimitFunction",
            handler="src.api.handlers.loss_limit.get_loss_limit_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-loss-limit",
            description="損失制限設定取得",
            **lambda_common_props,
        )

        set_loss_limit_fn = lambda_.Function(
            self,
            "SetLossLimitFunction",
            handler="src.api.handlers.loss_limit.set_loss_limit_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-set-loss-limit",
            description="損失制限設定作成",
            **lambda_common_props,
        )

        update_loss_limit_fn = lambda_.Function(
            self,
            "UpdateLossLimitFunction",
            handler="src.api.handlers.loss_limit.update_loss_limit_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-update-loss-limit",
            description="損失制限設定更新",
            **lambda_common_props,
        )

        check_loss_limit_fn = lambda_.Function(
            self,
            "CheckLossLimitFunction",
            handler="src.api.handlers.loss_limit.check_loss_limit_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-check-loss-limit",
            description="損失制限チェック",
            **lambda_common_props,
        )

        # ========================================
        # IPAT購入API
        # ========================================

        submit_purchase_fn = lambda_.Function(
            self,
            "SubmitPurchaseFunction",
            handler="src.api.handlers.purchase.submit_purchase_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-submit-purchase",
            description="購入実行",
            timeout=Duration.seconds(60),
            **{k: v for k, v in lambda_common_props.items() if k != "timeout"},
        )

        get_purchase_history_fn = lambda_.Function(
            self,
            "GetPurchaseHistoryFunction",
            handler="src.api.handlers.purchase.get_purchase_history_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-purchase-history",
            description="購入履歴取得",
            **lambda_common_props,
        )

        get_purchase_detail_fn = lambda_.Function(
            self,
            "GetPurchaseDetailFunction",
            handler="src.api.handlers.purchase.get_purchase_detail_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-purchase-detail",
            description="購入詳細取得",
            **lambda_common_props,
        )

        get_ipat_balance_fn = lambda_.Function(
            self,
            "GetIpatBalanceFunction",
            handler="src.api.handlers.ipat_balance.get_ipat_balance_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-ipat-balance",
            description="IPAT残高取得",
            timeout=Duration.seconds(30),
            **{k: v for k, v in lambda_common_props.items() if k != "timeout"},
        )

        save_ipat_credentials_fn = lambda_.Function(
            self,
            "SaveIpatCredentialsFunction",
            handler="src.api.handlers.ipat_settings.save_ipat_credentials_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-save-ipat-credentials",
            description="IPAT認証情報保存",
            **lambda_common_props,
        )

        get_ipat_status_fn = lambda_.Function(
            self,
            "GetIpatStatusFunction",
            handler="src.api.handlers.ipat_settings.get_ipat_status_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-ipat-status",
            description="IPAT設定ステータス取得",
            **lambda_common_props,
        )

        delete_ipat_credentials_fn = lambda_.Function(
            self,
            "DeleteIpatCredentialsFunction",
            handler="src.api.handlers.ipat_settings.delete_ipat_credentials_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-delete-ipat-credentials",
            description="IPAT認証情報削除",
            **lambda_common_props,
        )

        # ========================================
        # 投票記録API
        # ========================================

        create_betting_record_fn = lambda_.Function(
            self,
            "CreateBettingRecordFunction",
            handler="src.api.handlers.betting_record.create_betting_record_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-create-betting-record",
            description="投票記録作成",
            **lambda_common_props,
        )

        get_betting_records_fn = lambda_.Function(
            self,
            "GetBettingRecordsFunction",
            handler="src.api.handlers.betting_record.get_betting_records_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-betting-records",
            description="投票記録一覧取得",
            **lambda_common_props,
        )

        get_betting_summary_fn = lambda_.Function(
            self,
            "GetBettingSummaryFunction",
            handler="src.api.handlers.betting_record.get_betting_summary_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-betting-summary",
            description="投票成績サマリー取得",
            **lambda_common_props,
        )

        settle_betting_record_fn = lambda_.Function(
            self,
            "SettleBettingRecordFunction",
            handler="src.api.handlers.betting_record.settle_betting_record_handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-settle-betting-record",
            description="投票記録精算",
            **lambda_common_props,
        )

        # Cognito Post Confirmation トリガー
        cognito_post_confirmation_fn = lambda_.Function(
            self,
            "CognitoPostConfirmationFunction",
            handler="src.api.handlers.cognito_triggers.post_confirmation",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-cognito-post-confirmation",
            description="Cognito確認完了トリガー",
            **lambda_common_props,
        )

        # Post Confirmation トリガー設定
        user_pool.add_trigger(
            cognito.UserPoolOperation.POST_CONFIRMATION,
            cognito_post_confirmation_fn,
        )

        # USER_POOL_ID はアカウント削除Lambda にのみ設定
        # (PostConfirmation Lambdaに設定するとUserPoolとの循環依存が発生するため)
        delete_account_fn.add_environment("USER_POOL_ID", user_pool.user_pool_id)

        # アカウント削除Lambda に Cognito AdminDisableUser/AdminDeleteUser 権限
        delete_account_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminDisableUser",
                    "cognito-idp:AdminDeleteUser",
                ],
                resources=[user_pool.user_pool_arn],
            )
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

        # /users
        users = api.root.add_resource("users")

        # /users/profile
        users_profile = users.add_resource("profile")
        users_profile.add_method(
            "GET",
            apigw.LambdaIntegration(get_user_profile_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )
        users_profile.add_method(
            "PUT",
            apigw.LambdaIntegration(update_user_profile_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /users/account
        users_account = users.add_resource("account")
        users_account.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_account_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /users/loss-limit
        users_loss_limit = users.add_resource("loss-limit")
        users_loss_limit.add_method(
            "GET",
            apigw.LambdaIntegration(get_loss_limit_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )
        users_loss_limit.add_method(
            "POST",
            apigw.LambdaIntegration(set_loss_limit_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )
        users_loss_limit.add_method(
            "PUT",
            apigw.LambdaIntegration(update_loss_limit_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /users/loss-limit/check
        users_loss_limit_check = users_loss_limit.add_resource("check")
        users_loss_limit_check.add_method(
            "GET",
            apigw.LambdaIntegration(check_loss_limit_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /purchases
        purchases = api.root.add_resource("purchases")
        purchases.add_method(
            "POST",
            apigw.LambdaIntegration(submit_purchase_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )
        purchases.add_method(
            "GET",
            apigw.LambdaIntegration(get_purchase_history_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /purchases/{purchase_id}
        purchase = purchases.add_resource("{purchase_id}")
        purchase.add_method(
            "GET",
            apigw.LambdaIntegration(get_purchase_detail_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /ipat
        ipat = api.root.add_resource("ipat")

        # /ipat/balance
        ipat_balance = ipat.add_resource("balance")
        ipat_balance.add_method(
            "GET",
            apigw.LambdaIntegration(get_ipat_balance_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /settings
        settings = api.root.add_resource("settings")

        # /settings/ipat
        settings_ipat = settings.add_resource("ipat")
        settings_ipat.add_method(
            "GET",
            apigw.LambdaIntegration(get_ipat_status_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )
        settings_ipat.add_method(
            "PUT",
            apigw.LambdaIntegration(save_ipat_credentials_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )
        settings_ipat.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_ipat_credentials_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /betting-records
        betting_records = api.root.add_resource("betting-records")
        betting_records.add_method(
            "POST",
            apigw.LambdaIntegration(create_betting_record_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )
        betting_records.add_method(
            "GET",
            apigw.LambdaIntegration(get_betting_records_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /betting-records/summary
        betting_summary = betting_records.add_resource("summary")
        betting_summary.add_method(
            "GET",
            apigw.LambdaIntegration(get_betting_summary_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
        )

        # /betting-records/{record_id}/settle
        betting_record_by_id = betting_records.add_resource("{record_id}")
        betting_record_settle = betting_record_by_id.add_resource("settle")
        betting_record_settle.add_method(
            "PUT",
            apigw.LambdaIntegration(settle_betting_record_fn),
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=cognito_authorizer,
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
            timeout=Duration.seconds(120),  # API Gateway統合タイムアウトに合わせて延長
            memory_size=256,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                # agentcore CLIでデプロイしたAgentを参照
                "AGENTCORE_AGENT_ARN": agentcore_agent_arn,
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

        # AI予想テーブルへの読み取り権限
        ai_predictions_table.grant_read_data(agentcore_consultation_fn)
        speed_indices_table.grant_read_data(agentcore_consultation_fn)
        past_performances_table.grant_read_data(agentcore_consultation_fn)

        # /api/consultation
        api_resource = api.root.add_resource("api")
        consultation_resource = api_resource.add_resource("consultation")
        consultation_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                agentcore_consultation_fn,
                timeout=Duration.seconds(120),  # 統合タイムアウトを120秒に延長
            ),
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
            description="AI指数スクレイピング（ai-shisu.com / 毎晩21時に翌日分取得）",
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

        # 競馬AI ATHENA スクレイパー
        keiba_ai_athena_scraper_fn = lambda_.Function(
            self,
            "KeibaAiAthenaScraperFunction",
            handler="batch.keiba_ai_athena_scraper.handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
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
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
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
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
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

        # 競馬新聞＆スピード指数 スクレイパー
        jiro8_scraper_fn = lambda_.Function(
            self,
            "Jiro8SpeedIndexScraperFunction",
            handler="batch.jiro8_speed_index_scraper.handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
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
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
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
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
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

        # 競馬グラント スクレイパー
        keibagrant_scraper_fn = lambda_.Function(
            self,
            "KeibagrantScraperFunction",
            handler="batch.keibagrant_scraper.handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
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

        # EventBridge ルール（毎晩 21:00 JST = 12:00 UTC に翌日分を取得）
        scraper_rule = events.Rule(
            self,
            "AiShisuScraperRule",
            rule_name="baken-kaigi-ai-shisu-scraper-rule",
            description="AI指数スクレイピングを毎晩21:00 JSTに実行（翌日分を前日取得）",
            schedule=events.Schedule.cron(
                minute="0",
                hour="12",  # UTC 12:00 = JST 21:00
                month="*",
                week_day="*",
                year="*",
            ),
        )
        scraper_rule.add_target(targets.LambdaFunction(ai_shisu_scraper_fn))

        # --- AI予想スクレイパー EventBridge ルール ---

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

        # --- スピード指数スクレイパー EventBridge ルール ---

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

        # --- 馬柱スクレイパー EventBridge ルール ---

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

        # 無料競馬AI スクレイピング Lambda
        muryou_scraper_fn = lambda_.Function(
            self,
            "MuryouKeibaAiScraperFunction",
            handler="batch.muryou_keiba_ai_scraper.handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
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

        # EventBridge ルール: 当日朝 9:30 JST = 0:30 UTC（最終更新版を取得）
        muryou_morning_rule = events.Rule(
            self,
            "MuryouScraperMorningRule",
            rule_name="baken-kaigi-muryou-keiba-ai-scraper-morning-rule",
            description="無料競馬AI予想を当日朝9:30 JSTに取得（最終更新版）",
            schedule=events.Schedule.cron(
                minute="30",
                hour="0",  # UTC 0:30 = JST 9:30
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

        # EventBridge ルール: 前日夜 21:00 JST = 12:00 UTC（早期取得、当日朝に上書き）
        muryou_evening_rule = events.Rule(
            self,
            "MuryouScraperEveningRule",
            rule_name="baken-kaigi-muryou-keiba-ai-scraper-evening-rule",
            description="無料競馬AI予想を前日21:00 JSTに早期取得（翌日分）",
            schedule=events.Schedule.cron(
                minute="0",
                hour="12",  # UTC 12:00 = JST 21:00
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
        # JRAチェックサム自動更新バッチ
        # ========================================

        # JRAチェックサム更新 Lambda（VPC内からEC2にアクセス）
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

        if use_jravan:
            jra_checksum_updater_props["environment"]["JRAVAN_API_URL"] = jravan_api_url  # type: ignore

        jra_checksum_updater_fn = lambda_.Function(
            self,
            "JraChecksumUpdaterFunction",
            handler="batch.jra_checksum_updater.handler",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-jra-checksum-updater",
            description="JRA出馬表チェックサム自動更新",
            **jra_checksum_updater_props,
        )

        # EventBridge ルール（毎朝 6:10 JST = 21:10 UTC 前日、AI指数の10分後）
        checksum_rule = events.Rule(
            self,
            "JraChecksumUpdaterRule",
            rule_name="baken-kaigi-jra-checksum-updater-rule",
            description="JRAチェックサム自動更新を毎朝6:10 JSTに実行",
            schedule=events.Schedule.cron(
                minute="10",
                hour="21",  # UTC 21:10（前日） = JST 06:10（当日）
                month="*",
                week_day="*",
                year="*",
            ),
        )
        checksum_rule.add_target(targets.LambdaFunction(jra_checksum_updater_fn))

        # ========================================
        # DynamoDB アクセス権限
        # ========================================

        # カート関連 Lambda に Cart テーブルへのアクセス権限を付与
        cart_functions = [add_to_cart_fn, get_cart_fn, remove_from_cart_fn, clear_cart_fn]
        for fn in cart_functions:
            cart_table.grant_read_write_data(fn)

        # ユーザー関連 Lambda に User テーブルへのアクセス権限を付与
        user_functions = [get_user_profile_fn, update_user_profile_fn, delete_account_fn, cognito_post_confirmation_fn]
        for fn in user_functions:
            user_table.grant_read_write_data(fn)

        # 相談関連 Lambda に両テーブルへのアクセス権限を付与
        # （相談開始時にカートを参照するため）
        consultation_functions = [start_consultation_fn, send_message_fn, get_consultation_fn]
        for fn in consultation_functions:
            cart_table.grant_read_data(fn)
            session_table.grant_read_write_data(fn)

        # 損失制限関連 Lambda に User テーブルと LossLimitChange テーブルへのアクセス権限を付与
        # 読み取り専用 Lambda
        for fn in [get_loss_limit_fn, check_loss_limit_fn]:
            user_table.grant_read_data(fn)

        # get_loss_limit は change テーブルも読み取り
        loss_limit_change_table.grant_read_data(get_loss_limit_fn)

        # 書き込みが必要な Lambda
        for fn in [set_loss_limit_fn, update_loss_limit_fn]:
            user_table.grant_read_write_data(fn)
            loss_limit_change_table.grant_read_write_data(fn)

        # IPAT購入関連 Lambda に Purchase Order テーブルへのアクセス権限を付与
        purchase_functions = [
            submit_purchase_fn,
            get_purchase_history_fn,
            get_purchase_detail_fn,
        ]
        for fn in purchase_functions:
            purchase_order_table.grant_read_write_data(fn)

        # IPAT購入関連 Lambda に Cart テーブルへの読み取り権限を付与
        cart_table.grant_read_data(submit_purchase_fn)

        # SecretsManager 権限（IPAT認証情報の管理）
        ipat_secrets_policy = iam.PolicyStatement(
            actions=[
                "secretsmanager:GetSecretValue",
                "secretsmanager:CreateSecret",
                "secretsmanager:PutSecretValue",
                "secretsmanager:DeleteSecret",
                "secretsmanager:DescribeSecret",
            ],
            resources=[
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:baken-kaigi/ipat/*",
            ],
        )
        ipat_credential_functions = [
            submit_purchase_fn,
            get_ipat_balance_fn,
            save_ipat_credentials_fn,
            get_ipat_status_fn,
            delete_ipat_credentials_fn,
        ]
        for fn in ipat_credential_functions:
            fn.add_to_role_policy(ipat_secrets_policy)

        # 投票記録関連 Lambda に Betting Record テーブルへのアクセス権限を付与
        betting_record_functions = [
            create_betting_record_fn,
            get_betting_records_fn,
            get_betting_summary_fn,
            settle_betting_record_fn,
        ]
        for fn in betting_record_functions:
            betting_record_table.grant_read_write_data(fn)

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

        CfnOutput(
            self,
            "UserPoolId",
            value=user_pool.user_pool_id,
            description="Cognito User Pool ID",
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
        )

        CfnOutput(
            self,
            "UserPoolDomainUrl",
            value=f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
            description="Cognito User Pool Domain URL",
        )

        CfnOutput(
            self,
            "AgentCoreRuntimeRoleArn",
            value=agentcore_runtime_role.role_arn,
            description="AgentCore Runtime IAM Role ARN",
        )
