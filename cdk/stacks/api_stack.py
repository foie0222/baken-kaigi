"""馬券会議 API スタック."""
import os
from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
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

        # ========================================
        # Lambda Layer
        # ========================================
        deps_layer = lambda_.LayerVersion(
            self,
            "DepsLayer",
            code=lambda_.Code.from_asset(str(project_root / "cdk" / "lambda_layer")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Dependencies layer for baken-kaigi",
        )

        # 共通Lambda設定
        lambda_environment = {
            "PYTHONPATH": "/var/task:/opt/python",
            "CART_TABLE_NAME": cart_table.table_name,
            "SESSION_TABLE_NAME": session_table.table_name,
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

        # API Gateway
        api = apigw.RestApi(
            self,
            "BakenKaigiApi",
            rest_api_name="baken-kaigi-api",
            description="馬券会議 API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
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
            timeout=Duration.seconds(120),  # AgentCore のツール呼び出しに時間がかかる
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
            apigw.LambdaIntegration(
                agentcore_consultation_fn,
                timeout=Duration.seconds(29),  # API Gateway の最大タイムアウト
            ),
            api_key_required=True,
        )

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
