"""HRDB移行用 DynamoDB テーブルスタック."""
from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class HrdbTablesStack(Stack):
    """HRDB移行用 DynamoDB テーブル."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # races テーブル（PK: race_date, SK: race_id）
        self.races_table = dynamodb.Table(
            self,
            "RacesTable",
            table_name="baken-kaigi-races",
            partition_key=dynamodb.Attribute(
                name="race_date", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="race_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # runners テーブル（PK: race_id, SK: horse_number）
        self.runners_table = dynamodb.Table(
            self,
            "RunnersTable",
            table_name="baken-kaigi-runners",
            partition_key=dynamodb.Attribute(
                name="race_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="horse_number", type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )
        # GSI: horse_id-index（馬の過去成績検索用）
        self.runners_table.add_global_secondary_index(
            index_name="horse_id-index",
            partition_key=dynamodb.Attribute(
                name="horse_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="race_date", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # horses テーブル（PK: horse_id, SK: sk）
        self.horses_table = dynamodb.Table(
            self,
            "HorsesTable",
            table_name="baken-kaigi-horses",
            partition_key=dynamodb.Attribute(
                name="horse_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # jockeys テーブル（PK: jockey_id, SK: sk）
        self.jockeys_table = dynamodb.Table(
            self,
            "JockeysTable",
            table_name="baken-kaigi-jockeys",
            partition_key=dynamodb.Attribute(
                name="jockey_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # trainers テーブル（PK: trainer_id, SK: sk）
        self.trainers_table = dynamodb.Table(
            self,
            "TrainersTable",
            table_name="baken-kaigi-trainers",
            partition_key=dynamodb.Attribute(
                name="trainer_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )
