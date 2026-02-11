"""GitHub Actions OIDC 認証用スタック.

GitHub Actions から AWS リソースにアクセスするための
OIDC Provider と IAM Role を作成します。

このスタックは github_oidc=true コンテキストフラグを指定した場合のみ有効化されます。
例: cdk deploy GitHubOidcStack --context github_oidc=true
"""
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_iam as iam,
)
from constructs import Construct


class GitHubOidcStack(Stack):
    """GitHub Actions OIDC 認証用スタック."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        github_owner: str = "foie0222",
        github_repo: str = "baken-kaigi",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # GitHub OIDC Provider
        # thumbprints は GitHub Actions 公式ドキュメントで公開されている
        # token.actions.githubusercontent.com の証明書チェーンの SHA-1 フィンガープリントを設定する。
        # - 参考: https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
        # GitHub 側で証明書がローテーションされた場合は、上記ドキュメント等を参照して
        # 新しい thumbprint を確認し、このリストを更新・再デプロイすること。
        oidc_provider = iam.OpenIdConnectProvider(
            self,
            "GitHubOidcProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
            thumbprints=[
                # DigiCert High Assurance EV Root CA
                "6938fd4d98bab03faadb97b34396831e3780aea1",
                # DigiCert TLS Hybrid ECC SHA384 2020 CA1
                "1b511abead59b0b54b0a1c8232661093315d1fca",
            ],
        )

        # GitHub Actions ロールは、CDK Bootstrap で作成される
        # cdk-* 系ロールを AssumeRole するための最小権限のみを付与する。
        # 実際の AWS リソース操作権限は bootstrap 側ロールに集約する。
        # 
        # 完全一致のためStringEqualsを使用（ワイルドカードなし）
        deploy_role = iam.Role(
            self,
            "GitHubActionsDeployRole",
            role_name="github-actions-deploy-role",
            assumed_by=iam.FederatedPrincipal(
                federated=oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                        "token.actions.githubusercontent.com:sub": f"repo:{github_owner}/{github_repo}:ref:refs/heads/main",
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
            description="IAM Role for GitHub Actions CDK/AgentCore deployment",
        )

        # CDK Bootstrap ロールへの AssumeRole 権限
        # 現在のアカウントのみに制限し、bootstrap 標準のプレフィックスを使用
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="AssumeBootstrapRoles",
                effect=iam.Effect.ALLOW,
                actions=[
                    "sts:AssumeRole",
                ],
                resources=[
                    f"arn:aws:iam::{Stack.of(self).account}:role/cdk-hnb659fds-*",
                ],
            )
        )

        # AgentCore デプロイに必要な最小権限
        # CDK以外のデプロイ（AgentCore CLI等）で必要な権限を追加
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCore",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:*",
                    "bedrock-agentcore:*",
                ],
                resources=["*"],
            )
        )

        # SSM SendCommand（EC2デプロイ用）
        # SSMドキュメントは無条件で許可、EC2インスタンスはタグで制限
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="SsmSendCommandDocument",
                actions=["ssm:SendCommand"],
                resources=[
                    f"arn:aws:ssm:ap-northeast-1::document/AWS-RunPowerShellScript",
                ],
            )
        )
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="SsmSendCommandInstance",
                actions=["ssm:SendCommand"],
                resources=[
                    f"arn:aws:ec2:ap-northeast-1:{Stack.of(self).account}:instance/*",
                ],
                conditions={
                    "StringEquals": {
                        "ssm:resourceTag/app": "jravan-api",
                    },
                },
            )
        )
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="SsmGetCommandInvocation",
                actions=["ssm:GetCommandInvocation"],
                resources=["*"],
            )
        )

        # S3デプロイアーティファクト書き込み
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3DeployUpload",
                actions=["s3:PutObject", "s3:GetObject"],
                resources=[
                    f"arn:aws:s3:::baken-kaigi-jravan-deploy-{Stack.of(self).account}/deploy/*",
                ],
            )
        )

        # CloudFormation ExportsからインスタンスID・バケット名取得
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudFormationListExports",
                actions=["cloudformation:ListExports"],
                resources=["*"],
            )
        )

        # Outputs
        CfnOutput(
            self,
            "DeployRoleArn",
            value=deploy_role.role_arn,
            description="GitHub Actions Deploy Role ARN (set in GitHub Secrets)",
            export_name="GitHubActionsDeployRoleArn",
        )

        CfnOutput(
            self,
            "OidcProviderArn",
            value=oidc_provider.open_id_connect_provider_arn,
            description="GitHub OIDC Provider ARN",
            export_name="GitHubOidcProviderArn",
        )
