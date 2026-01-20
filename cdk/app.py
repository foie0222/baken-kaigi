#!/usr/bin/env python3
"""CDK アプリケーションエントリーポイント.

Usage:
    # モック環境（デフォルト）
    cdk deploy BakenKaigiApiStack

    # JRA-VAN 連携環境（EC2 + Lambda in VPC）
    cdk deploy --all --context jravan=true

    # 既存 VPC を使用する場合
    cdk deploy --all --context jravan=true --context vpc_id=vpc-xxxxxxxxx
"""
import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2

from stacks.api_stack import BakenKaigiApiStack
from stacks.jravan_server_stack import JraVanServerStack

app = cdk.App()

# コンテキストから設定を取得
use_jravan = app.node.try_get_context("jravan") == "true"
vpc_id = app.node.try_get_context("vpc_id")

# 環境設定
env = cdk.Environment(
    account=None,  # 環境変数 CDK_DEFAULT_ACCOUNT から取得
    region="ap-northeast-1",
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
        env=env,
    )

app.synth()
