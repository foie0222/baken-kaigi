#!/usr/bin/env python3
"""CDK アプリケーションエントリーポイント."""
import aws_cdk as cdk

from stacks.api_stack import BakenKaigiApiStack

app = cdk.App()

BakenKaigiApiStack(
    app,
    "BakenKaigiApiStack",
    env=cdk.Environment(
        account=None,  # 環境変数から取得
        region="ap-northeast-1",
    ),
)

app.synth()
