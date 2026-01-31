#!/usr/bin/env python3
"""CDK アプリケーションエントリーポイント.

Usage:
    # モック環境（デフォルト）
    cdk deploy BakenKaigiApiStack

    # JRA-VAN 連携環境（EC2 + Lambda in VPC）
    cdk deploy --all --context jravan=true

    # 既存 VPC を使用する場合
    cdk deploy --all --context jravan=true --context vpc_id=vpc-xxxxxxxxx

    # 開発用オリジン（localhost）を許可する場合
    # 注意: 本番環境では絶対に使用しないこと
    cdk deploy --all --context jravan=true --context allow_dev_origins=true

    # GitHub OIDC スタックをデプロイ（初回セットアップ時のみ）
    # 注意: このスタックは明示的に github_oidc=true を指定した場合のみデプロイされます
    cdk deploy GitHubOidcStack --context github_oidc=true
"""
import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2

from stacks.api_stack import BakenKaigiApiStack
from stacks.jravan_server_stack import JraVanServerStack
from stacks.github_oidc_stack import GitHubOidcStack

app = cdk.App()

# コンテキストから設定を取得
use_jravan = app.node.try_get_context("jravan") == "true"
use_github_oidc = app.node.try_get_context("github_oidc") == "true"
allow_dev_origins = app.node.try_get_context("allow_dev_origins") == "true"
vpc_id = app.node.try_get_context("vpc_id")

# 環境設定
env = cdk.Environment(
    account=None,  # 環境変数 CDK_DEFAULT_ACCOUNT から取得
    region="ap-northeast-1",
)

# GitHub OIDC スタック（明示的に有効化された場合のみ）
# 初回セットアップ時: cdk deploy GitHubOidcStack --context github_oidc=true
if use_github_oidc:
    GitHubOidcStack(
        app,
        "GitHubOidcStack",
        env=env,
    )

if use_jravan:
    # ========================================
    # JRA-VAN 連携モード
    # EC2 Windows + Lambda in VPC
    # ========================================

    # VPC の取得または作成
    if vpc_id:
        # 既存 VPC を使用
        # 注意: cdk synth 前に `cdk context` でキャッシュが必要
        vpc = ec2.Vpc.from_lookup(
            app,
            "ExistingVpc",
            vpc_id=vpc_id,
        )
        jravan_stack = JraVanServerStack(
            app,
            "JraVanServerStack",
            vpc=vpc,
            env=env,
        )
    else:
        # 新規 VPC を JraVanServerStack 内で作成
        jravan_stack = JraVanServerStack(
            app,
            "JraVanServerStack",
            env=env,
        )

    # API スタック（JRA-VAN 連携）
    BakenKaigiApiStack(
        app,
        "BakenKaigiApiStack",
        vpc=jravan_stack.vpc,
        jravan_api_url=jravan_stack.api_url,
        allow_dev_origins=allow_dev_origins,
        env=env,
    )

else:
    # ========================================
    # モックモード（デフォルト）
    # VPC 不要、MockRaceDataProvider を使用
    # ========================================
    BakenKaigiApiStack(
        app,
        "BakenKaigiApiStack",
        allow_dev_origins=allow_dev_origins,
        env=env,
    )

app.synth()
