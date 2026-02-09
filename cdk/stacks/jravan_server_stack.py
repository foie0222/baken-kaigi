"""JRA-VAN API サーバースタック.

EC2 Windows インスタンスを作成し、JRA-VAN Data Lab. の
JV-Link を動作させる FastAPI サーバーをホストする。
"""
from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
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

            # Secrets Manager VPC Interface Endpoint
            # Lambda（ISOLATED サブネット）から Secrets Manager へアクセスするために必要
            self.vpc.add_interface_endpoint(
                "SecretsManagerEndpoint",
                service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
                subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                ),
            )
        else:
            self.vpc = vpc

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
