"""馬券会議 API スタック."""
from pathlib import Path

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from constructs import Construct


class BakenKaigiApiStack(Stack):
    """馬券会議 API スタック.

    Lambda + API Gateway + DynamoDB でサーバーレス API を構築する。
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # プロジェクトルートディレクトリ
        project_root = Path(__file__).parent.parent.parent

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
        lambda_common_props = {
            "runtime": lambda_.Runtime.PYTHON_3_12,
            "timeout": Duration.seconds(30),
            "memory_size": 256,
            "layers": [deps_layer],
            "environment": {
                "PYTHONPATH": "/var/task:/opt/python",
                "CART_TABLE_NAME": cart_table.table_name,
                "SESSION_TABLE_NAME": session_table.table_name,
                "CODE_VERSION": "4",  # コード更新強制用
            },
        }

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
                allow_headers=["Content-Type", "Authorization"],
            ),
        )

        # エンドポイント定義
        # /races
        races = api.root.add_resource("races")
        races.add_method("GET", apigw.LambdaIntegration(get_races_fn))

        # /races/{race_id}
        race = races.add_resource("{race_id}")
        race.add_method("GET", apigw.LambdaIntegration(get_race_detail_fn))

        # /cart
        cart = api.root.add_resource("cart")

        # /cart/items
        cart_items = cart.add_resource("items")
        cart_items.add_method("POST", apigw.LambdaIntegration(add_to_cart_fn))

        # /cart/{cart_id}
        cart_by_id = cart.add_resource("{cart_id}")
        cart_by_id.add_method("GET", apigw.LambdaIntegration(get_cart_fn))
        cart_by_id.add_method("DELETE", apigw.LambdaIntegration(clear_cart_fn))

        # /cart/{cart_id}/items/{item_id}
        cart_items_by_id = cart_by_id.add_resource("items").add_resource("{item_id}")
        cart_items_by_id.add_method("DELETE", apigw.LambdaIntegration(remove_from_cart_fn))

        # /consultations
        consultations = api.root.add_resource("consultations")
        consultations.add_method("POST", apigw.LambdaIntegration(start_consultation_fn))

        # /consultations/{session_id}
        consultation = consultations.add_resource("{session_id}")
        consultation.add_method("GET", apigw.LambdaIntegration(get_consultation_fn))

        # /consultations/{session_id}/messages
        messages = consultation.add_resource("messages")
        messages.add_method("POST", apigw.LambdaIntegration(send_message_fn))

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
