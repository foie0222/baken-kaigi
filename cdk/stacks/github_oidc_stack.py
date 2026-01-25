"""GitHub Actions OIDC 認証用スタック.

GitHub Actions から AWS リソースにアクセスするための
OIDC Provider と IAM Role を作成します。
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
        # 既存の Provider がある場合はインポートも可能
        oidc_provider = iam.OpenIdConnectProvider(
            self,
            "GitHubOidcProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
            thumbprints=["ffffffffffffffffffffffffffffffffffffffff"],  # GitHub は thumbprint 検証不要
        )

        # デプロイ用 IAM Role
        deploy_role = iam.Role(
            self,
            "GitHubActionsDeployRole",
            role_name="github-actions-deploy-role",
            assumed_by=iam.FederatedPrincipal(
                federated=oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": f"repo:{github_owner}/{github_repo}:ref:refs/heads/main",
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
            description="GitHub Actions からの CDK/AgentCore デプロイ用ロール",
        )

        # CDK デプロイに必要な権限
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudFormation",
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudformation:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="Lambda",
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="APIGateway",
                effect=iam.Effect.ALLOW,
                actions=[
                    "apigateway:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="DynamoDB",
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="IAM",
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="EC2",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="SSM",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ssm:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogs",
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="Bedrock",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:*",
                    "bedrock-agentcore:*",
                ],
                resources=["*"],
            )
        )

        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="STS",
                effect=iam.Effect.ALLOW,
                actions=[
                    "sts:AssumeRole",
                ],
                resources=["arn:aws:iam::*:role/cdk-*"],
            )
        )

        # Outputs
        CfnOutput(
            self,
            "DeployRoleArn",
            value=deploy_role.role_arn,
            description="GitHub Actions デプロイ用ロール ARN（GitHub Secrets に設定）",
            export_name="GitHubActionsDeployRoleArn",
        )

        CfnOutput(
            self,
            "OidcProviderArn",
            value=oidc_provider.open_id_connect_provider_arn,
            description="GitHub OIDC Provider ARN",
            export_name="GitHubOidcProviderArn",
        )
