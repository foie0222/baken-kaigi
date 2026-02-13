#!/usr/bin/env python3
"""CDK アプリケーションエントリーポイント.

Usage:
    # モック環境（デフォルト）- 順次デプロイ（Lambda名の競合回避のため）
    cdk deploy BakenKaigiApiStack --require-approval never
    cdk deploy BakenKaigiBatchStack --require-approval never

    # JRA-VAN 連携環境（EC2 + Lambda in VPC）- 順次デプロイ
    cdk deploy BakenKaigiApiStack --context jravan=true --require-approval never
    cdk deploy BakenKaigiBatchStack --context jravan=true --require-approval never

    # 開発用オリジン（localhost）を許可する場合
    # 注意: 本番環境では絶対に使用しないこと
    cdk deploy --all --context jravan=true --context allow_dev_origins=true

    # GitHub OIDC スタックをデプロイ（初回セットアップ時のみ）
    # 注意: このスタックは明示的に github_oidc=true を指定した場合のみデプロイされます
    cdk deploy GitHubOidcStack --context github_oidc=true
"""
import aws_cdk as cdk

from stacks.api_stack import BakenKaigiApiStack
from stacks.batch_stack import BakenKaigiBatchStack
from stacks.jravan_server_stack import JraVanServerStack
from stacks.github_oidc_stack import GitHubOidcStack
from stacks.monitoring_stack import BakenKaigiMonitoringStack

app = cdk.App()

# コンテキストから設定を取得
use_jravan = app.node.try_get_context("jravan") == "true"
use_github_oidc = app.node.try_get_context("github_oidc") == "true"
allow_dev_origins = app.node.try_get_context("allow_dev_origins") == "true"

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
    jravan_stack = JraVanServerStack(
        app,
        "JraVanServerStack",
        instance_type="t3.nano",
        env=env,
        termination_protection=True,
    )

    # API スタック（JRA-VAN 連携）
    api_stack = BakenKaigiApiStack(
        app,
        "BakenKaigiApiStack",
        vpc=jravan_stack.vpc,
        jravan_api_url=jravan_stack.api_url,
        allow_dev_origins=allow_dev_origins,
        env=env,
    )

    # バッチ処理スタック（JRA-VAN 連携）
    # ApiStack を先にデプロイして旧バッチリソースを削除してから
    # BatchStack をデプロイする（同名 Lambda の競合防止）
    batch_stack = BakenKaigiBatchStack(
        app,
        "BakenKaigiBatchStack",
        vpc=jravan_stack.vpc,
        jravan_api_url=jravan_stack.api_url,
        env=env,
    )
    batch_stack.add_dependency(api_stack)

else:
    # ========================================
    # モックモード（デフォルト）
    # VPC 不要、MockRaceDataProvider を使用
    # ========================================
    api_stack = BakenKaigiApiStack(
        app,
        "BakenKaigiApiStack",
        allow_dev_origins=allow_dev_origins,
        env=env,
    )

    # バッチ処理スタック（モックモード）
    # ApiStack を先にデプロイして旧バッチリソースを削除してから
    # BatchStack をデプロイする（同名 Lambda の競合防止）
    batch_stack = BakenKaigiBatchStack(
        app,
        "BakenKaigiBatchStack",
        env=env,
    )
    batch_stack.add_dependency(api_stack)

# モニタリングスタック（CloudWatch ダッシュボード）
BakenKaigiMonitoringStack(
    app,
    "BakenKaigiMonitoringStack",
    env=env,
)

app.synth()
