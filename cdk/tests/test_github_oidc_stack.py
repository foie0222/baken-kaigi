"""GitHub OIDC Stack テスト."""
import sys
from pathlib import Path

import pytest

# プロジェクトルート（cdk/）をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def template():
    """CloudFormationテンプレートを生成.

    scope="module"により、このファイル内で1回のみスタック合成を実行。
    テストはテンプレートを読み取るのみで変更しないため、共有可能。
    """
    import aws_cdk as cdk
    from aws_cdk import assertions

    from stacks.github_oidc_stack import GitHubOidcStack

    app = cdk.App()
    stack = GitHubOidcStack(
        app,
        "TestGitHubOidcStack",
        env=cdk.Environment(account="123456789012", region="ap-northeast-1"),
    )
    return assertions.Template.from_stack(stack)


@pytest.fixture(scope="module")
def template_custom_repo():
    """カスタムリポジトリ設定のCloudFormationテンプレートを生成.

    TestGitHubOidcStackCustomOwnerRepo用。scope="module"で1回のみ合成。
    """
    import aws_cdk as cdk
    from aws_cdk import assertions

    from stacks.github_oidc_stack import GitHubOidcStack

    app = cdk.App()
    stack = GitHubOidcStack(
        app,
        "TestCustomStack",
        github_owner="custom-org",
        github_repo="custom-repo",
        env=cdk.Environment(account="123456789012", region="ap-northeast-1"),
    )
    return assertions.Template.from_stack(stack)


class TestGitHubOidcStack:
    """GitHub OIDCスタックのテスト."""

    def test_oidc_provider_created(self, template):
        """OIDC Providerが作成されること."""
        # OpenIdConnectProvider はカスタムリソースで作成される
        template.has_resource_properties(
            "Custom::AWSCDKOpenIdConnectProvider",
            {
                "Url": "https://token.actions.githubusercontent.com",
                "ClientIDList": ["sts.amazonaws.com"],
            },
        )

    def test_oidc_provider_thumbprints(self, template):
        """OIDC Providerに正しいthumbprintsが設定されること."""
        template.has_resource_properties(
            "Custom::AWSCDKOpenIdConnectProvider",
            {
                "ThumbprintList": [
                    "6938fd4d98bab03faadb97b34396831e3780aea1",
                    "1b511abead59b0b54b0a1c8232661093315d1fca",
                ],
            },
        )

    def test_iam_role_created(self, template):
        """IAM Roleが作成されること."""
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "RoleName": "github-actions-deploy-role",
                "Description": "IAM Role for GitHub Actions CDK/AgentCore deployment",
            },
        )

    def test_iam_role_trust_policy_conditions(self, template):
        """IAM Roleの信頼ポリシーに正しい条件が設定されること."""
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRoleWithWebIdentity",
                            "Condition": {
                                "StringEquals": {
                                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                                    "token.actions.githubusercontent.com:sub": "repo:foie0222/baken-kaigi:ref:refs/heads/main",
                                },
                            },
                            "Effect": "Allow",
                        }
                    ],
                },
            },
        )

    def test_iam_role_assume_bootstrap_roles_policy(self, template):
        """Bootstrap ロールへの AssumeRole 権限が設定されること."""
        from aws_cdk.assertions import Match

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "AssumeBootstrapRoles",
                                    "Action": "sts:AssumeRole",
                                    "Effect": "Allow",
                                    "Resource": "arn:aws:iam::123456789012:role/cdk-hnb659fds-*",
                                }
                            ),
                        ]
                    ),
                },
            },
        )

    def test_iam_role_bedrock_policy(self, template):
        """Bedrock/AgentCore 権限が設定されること."""
        from aws_cdk.assertions import Match

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "BedrockAgentCore",
                                    "Action": ["bedrock:*", "bedrock-agentcore:*"],
                                    "Effect": "Allow",
                                    "Resource": "*",
                                }
                            ),
                        ]
                    ),
                },
            },
        )

    def test_iam_role_ssm_send_command_policy(self, template):
        """SSM SendCommand 権限がタグベース条件付きで設定されること."""
        from aws_cdk.assertions import Match

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "SsmSendCommandInstance",
                                    "Action": "ssm:SendCommand",
                                    "Condition": {
                                        "StringEquals": {
                                            "ssm:resourceTag/app": "jravan-api",
                                        },
                                    },
                                }
                            ),
                        ]
                    ),
                },
            },
        )

    def test_iam_role_s3_deploy_upload_policy(self, template):
        """S3デプロイアーティファクト書き込み権限が設定されること."""
        from aws_cdk.assertions import Match

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "S3DeployUpload",
                                    "Action": Match.array_with(
                                        ["s3:PutObject", "s3:GetObject"]
                                    ),
                                }
                            ),
                        ]
                    ),
                },
            },
        )

    def test_iam_role_cloudformation_list_exports_policy(self, template):
        """CloudFormation ListExports 権限が設定されること."""
        from aws_cdk.assertions import Match

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "CloudFormationListExports",
                                    "Action": "cloudformation:ListExports",
                                }
                            ),
                        ]
                    ),
                },
            },
        )

    def test_iam_role_agentcore_s3_upload_policy(self, template):
        """AgentCore S3アップロード権限が設定されること."""
        from aws_cdk.assertions import Match

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "AgentCoreS3Upload",
                                    "Action": Match.array_with(
                                        ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
                                    ),
                                }
                            ),
                        ]
                    ),
                },
            },
        )

    def test_iam_role_agentcore_pass_role_policy(self, template):
        """AgentCore PassRole権限がCDK管理ロールに対して設定されること."""
        from aws_cdk.assertions import Match

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "AgentCorePassRole",
                                    "Action": "iam:PassRole",
                                    "Resource": Match.string_like_regexp(
                                        ".*:role/baken-kaigi-agentcore-runtime-role$"
                                    ),
                                }
                            ),
                        ]
                    ),
                },
            },
        )

    def test_deploy_role_arn_output(self, template):
        """DeployRoleArn出力が存在すること."""
        template.has_output(
            "DeployRoleArn",
            {
                "Export": {"Name": "GitHubActionsDeployRoleArn"},
            },
        )

    def test_oidc_provider_arn_output(self, template):
        """OidcProviderArn出力が存在すること."""
        template.has_output(
            "OidcProviderArn",
            {
                "Export": {"Name": "GitHubOidcProviderArn"},
            },
        )


class TestGitHubOidcStackCustomOwnerRepo:
    """カスタム owner/repo 設定のテスト."""

    def test_custom_owner_repo(self, template_custom_repo):
        """カスタムの owner/repo を設定できること."""
        template_custom_repo.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Condition": {
                                "StringEquals": {
                                    "token.actions.githubusercontent.com:sub": "repo:custom-org/custom-repo:ref:refs/heads/main",
                                },
                            },
                        }
                    ],
                },
            },
        )
