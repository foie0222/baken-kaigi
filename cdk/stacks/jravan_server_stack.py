"""JRA-VAN API サーバースタック.

EC2 Windows インスタンスを作成し、JRA-VAN Data Lab. の
JV-Link を動作させる FastAPI サーバーをホストする。
"""
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from constructs import Construct


class JraVanServerStack(Stack):
    """JRA-VAN API サーバー用 EC2 スタック.

    JV-Link は 32bit Windows COM コンポーネントのため、
    Lambda から直接利用できない。EC2 Windows を中継サーバーとして使用する。
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc | None = None,
        instance_type: str = "t3.small",
        volume_size: int = 50,
        **kwargs,
    ) -> None:
        """スタックを初期化する.

        Args:
            scope: CDK スコープ
            construct_id: コンストラクト ID
            vpc: 使用する VPC（None の場合は新規作成）
            instance_type: EC2 インスタンスタイプ
            volume_size: EBS ボリュームサイズ（GB）
            **kwargs: その他のスタックパラメータ
        """
        super().__init__(scope, construct_id, **kwargs)

        # ========================================
        # VPC
        # NAT Gateway は使用しない（コスト削減）
        # Lambda → DynamoDB は VPC Gateway Endpoint 経由
        # Lambda → EC2 は VPC 内通信
        # EC2 → インターネット はパブリックサブネット + IGW
        # ========================================
        if vpc is None:
            self.vpc = ec2.Vpc(
                self,
                "JraVanVpc",
                vpc_name="jravan-vpc",
                max_azs=2,
                nat_gateways=0,  # NAT Gateway 不使用（コスト削減）
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="Public",
                        subnet_type=ec2.SubnetType.PUBLIC,
                        cidr_mask=24,
                    ),
                    ec2.SubnetConfiguration(
                        name="Private",
                        subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                        cidr_mask=24,
                    ),
                ],
            )

            # DynamoDB VPC Gateway Endpoint（無料）
            self.vpc.add_gateway_endpoint(
                "DynamoDbEndpoint",
                service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
            )
        else:
            self.vpc = vpc

        # Secrets Manager VPC Interface Endpoint
        # Lambda（ISOLATED サブネット）から Secrets Manager へアクセスするために必要
        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
        )

        # ========================================
        # デプロイ用 S3 バケット
        # GitHub Actions → S3 → EC2 でデプロイアーティファクトを配布
        # ========================================
        self.deploy_bucket = s3.Bucket(
            self,
            "JraVanDeployBucket",
            bucket_name=f"baken-kaigi-jravan-deploy-{Stack.of(self).account}",
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(7), prefix="deploy/"),
            ],
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # ========================================
        # セキュリティグループ
        # ========================================
        self.security_group = ec2.SecurityGroup(
            self,
            "JraVanApiSG",
            vpc=self.vpc,
            security_group_name="jravan-api-sg",
            description="Security group for JRA-VAN API server",
            allow_all_outbound=True,
        )

        # VPC 内からの FastAPI アクセスを許可
        self.security_group.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(8000),
            "Allow FastAPI from VPC",
        )

        # ========================================
        # IAM ロール（SSM Session Manager 用）
        # ========================================
        role = iam.Role(
            self,
            "JraVanApiRole",
            role_name="jravan-api-ec2-role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                # Session Manager でのリモート接続を許可
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        # EC2 から S3 デプロイバケットの読み取りを許可
        self.deploy_bucket.grant_read(role)

        # ========================================
        # キーペア（Fleet Manager RDP 用）
        # ========================================
        self.key_pair = ec2.KeyPair(
            self,
            "JraVanApiKeyPair",
            key_pair_name="jravan-api-keypair",
            type=ec2.KeyPairType.RSA,
        )

        # ========================================
        # Windows Server 2022 AMI
        # ========================================
        windows_ami = ec2.MachineImage.latest_windows(
            ec2.WindowsVersion.WINDOWS_SERVER_2022_JAPANESE_FULL_BASE
        )

        # ========================================
        # EC2 インスタンス
        # パブリックサブネットに配置（NAT Gateway 不要）
        # ========================================
        self.instance = ec2.Instance(
            self,
            "JraVanApiInstance",
            instance_name="jravan-api-server",
            instance_type=ec2.InstanceType(instance_type),
            machine_image=windows_ami,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            security_group=self.security_group,
            role=role,
            key_pair=self.key_pair,
            associate_public_ip_address=True,  # パブリック IP を付与
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/sda1",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=volume_size,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=True,
                    ),
                )
            ],
            # UserData で初期セットアップスクリプトを実行
            user_data=self._create_user_data(),
        )

        # SSM SendCommand のタグベース権限制御用
        Tags.of(self.instance).add("app", "jravan-api")

        # ========================================
        # EC2 スケジューラー（コスト最適化）
        # 土曜 AM6:00 JST に起動、日曜 PM23:00 JST に停止
        # ========================================
        self._create_ec2_scheduler()

        # ========================================
        # 出力
        # ========================================
        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name="JraVanVpcId",
        )

        CfnOutput(
            self,
            "InstanceId",
            value=self.instance.instance_id,
            description="EC2 Instance ID",
            export_name="JraVanInstanceId",
        )

        CfnOutput(
            self,
            "PrivateIp",
            value=self.instance.instance_private_ip,
            description="JRA-VAN API Server Private IP",
            export_name="JraVanPrivateIp",
        )

        CfnOutput(
            self,
            "ApiUrl",
            value=f"http://{self.instance.instance_private_ip}:8000",
            description="JRA-VAN API URL for Lambda environment variable",
            export_name="JraVanApiUrl",
        )

        CfnOutput(
            self,
            "SecurityGroupId",
            value=self.security_group.security_group_id,
            description="Security Group ID",
            export_name="JraVanSecurityGroupId",
        )

        CfnOutput(
            self,
            "KeyPairName",
            value=self.key_pair.key_pair_name,
            description="Key Pair Name for RDP access",
        )

        CfnOutput(
            self,
            "KeyPairParameterName",
            value=f"/ec2/keypair/{self.key_pair.key_pair_id}",
            description="SSM Parameter for private key (use for Fleet Manager RDP)",
        )

        CfnOutput(
            self,
            "DeployBucketName",
            value=self.deploy_bucket.bucket_name,
            export_name="JraVanDeployBucketName",
        )

    def _create_ec2_scheduler(self) -> None:
        """EC2 インスタンスのスケジュール起動/停止を設定する.

        EventBridge Rule + Lambda で土日の競馬開催時間帯のみ起動する。
        - 起動: 土曜 AM6:00 JST = UTC 金曜 21:00
        - 停止: 日曜 PM23:00 JST = UTC 日曜 14:00
        """
        # Lambda 用 IAM ロール
        scheduler_role = iam.Role(
            self,
            "Ec2SchedulerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # EC2 起動/停止の権限（対象インスタンスに限定）
        scheduler_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ec2:StartInstances", "ec2:StopInstances"],
                resources=[
                    f"arn:aws:ec2:{Stack.of(self).region}:{Stack.of(self).account}"
                    f":instance/{self.instance.instance_id}",
                ],
            )
        )

        # Lambda 関数
        scheduler_fn = lambda_.Function(
            self,
            "Ec2SchedulerFunction",
            function_name="jravan-ec2-scheduler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambda/ec2_scheduler"),
            timeout=Duration.seconds(30),
            environment={
                "INSTANCE_ID": self.instance.instance_id,
            },
            role=scheduler_role,
        )

        # EventBridge Rule: 土曜 AM6:00 JST に起動（UTC 金曜 21:00）
        start_rule = events.Rule(
            self,
            "Ec2StartRule",
            rule_name="jravan-ec2-start",
            schedule=events.Schedule.cron(
                minute="0", hour="21", week_day="FRI",
            ),
        )
        start_rule.add_target(
            targets.LambdaFunction(
                scheduler_fn,
                event=events.RuleTargetInput.from_object({"action": "start"}),
            )
        )

        # EventBridge Rule: 日曜 PM23:00 JST に停止（UTC 日曜 14:00）
        stop_rule = events.Rule(
            self,
            "Ec2StopRule",
            rule_name="jravan-ec2-stop",
            schedule=events.Schedule.cron(
                minute="0", hour="14", week_day="SUN",
            ),
        )
        stop_rule.add_target(
            targets.LambdaFunction(
                scheduler_fn,
                event=events.RuleTargetInput.from_object({"action": "stop"}),
            )
        )

    def _create_user_data(self) -> ec2.UserData:
        """EC2 起動時の初期化スクリプトを作成する."""
        user_data = ec2.UserData.for_windows()

        # PowerShell スクリプトで初期セットアップ
        user_data.add_commands(
            # 作業ディレクトリ作成
            "New-Item -ItemType Directory -Force -Path C:\\jravan-api",
            "New-Item -ItemType Directory -Force -Path C:\\setup",
            # Python 3.11 (32bit) ダウンロード
            "$pythonUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe'",
            "Invoke-WebRequest -Uri $pythonUrl -OutFile C:\\setup\\python-3.11.9.exe",
            # Python インストール（サイレント、PATH追加）
            "Start-Process -FilePath C:\\setup\\python-3.11.9.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait",
            # 環境変数を再読み込み
            "$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')",
            # pip でパッケージインストール
            "python -m pip install --upgrade pip",
            "pip install fastapi uvicorn pywin32 requests",
            # NSSM ダウンロード（サービス化用）
            "$nssmUrl = 'https://nssm.cc/release/nssm-2.24.zip'",
            "Invoke-WebRequest -Uri $nssmUrl -OutFile C:\\setup\\nssm.zip",
            "Expand-Archive -Path C:\\setup\\nssm.zip -DestinationPath C:\\setup -Force",
            "Copy-Item C:\\setup\\nssm-2.24\\win64\\nssm.exe C:\\Windows\\System32\\",
            # セットアップ完了フラグ
            "New-Item -ItemType File -Force -Path C:\\setup\\setup_complete.txt",
            "'Python and dependencies installed successfully' | Out-File C:\\setup\\setup_complete.txt",
        )

        return user_data

    @property
    def api_url(self) -> str:
        """API URL を取得する."""
        return f"http://{self.instance.instance_private_ip}:8000"
