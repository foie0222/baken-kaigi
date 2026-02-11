"""馬券会議 モニタリングスタック.

AgentCore ツールの CloudWatch ダッシュボードを作成する。
"""

from aws_cdk import Stack
from aws_cdk import aws_cloudwatch as cloudwatch
from constructs import Construct

# AgentCore ツール一覧
TOOL_NAMES = [
    "get_ai_prediction",
    "get_speed_index",
    "list_speed_indices_for_date",
    "get_past_performance",
    "get_race_runners",
    "analyze_bet_selection",
    "analyze_odds_movement",
    "analyze_race_characteristics",
    "analyze_risk_factors",
    "generate_bet_proposal",
]

METRICS_NAMESPACE = "BakenKaigi/AgentTools"


class BakenKaigiMonitoringStack(Stack):
    """馬券会議 モニタリングスタック.

    AgentCore ツールの実行時間・呼び出し回数・エラー数を可視化する
    CloudWatch ダッシュボードを作成する。
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        dashboard = cloudwatch.Dashboard(
            self,
            "AgentToolsDashboard",
            dashboard_name="baken-kaigi-agent-tools",
        )

        # ツール実行時間（平均）
        execution_time_metrics = [
            cloudwatch.Metric(
                namespace=METRICS_NAMESPACE,
                metric_name="ExecutionTime",
                dimensions_map={"ToolName": name},
                statistic="Average",
                label=name,
            )
            for name in TOOL_NAMES
        ]

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="ツール実行時間（平均）",
                left=execution_time_metrics,
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="ツール実行時間（p99）",
                left=[
                    cloudwatch.Metric(
                        namespace=METRICS_NAMESPACE,
                        metric_name="ExecutionTime",
                        dimensions_map={"ToolName": name},
                        statistic="p99",
                        label=name,
                    )
                    for name in TOOL_NAMES
                ],
                width=12,
            ),
        )

        # 呼び出し回数
        invocation_metrics = [
            cloudwatch.Metric(
                namespace=METRICS_NAMESPACE,
                metric_name="Invocations",
                dimensions_map={"ToolName": name},
                statistic="Sum",
                label=name,
            )
            for name in TOOL_NAMES
        ]

        # エラー数
        error_metrics = [
            cloudwatch.Metric(
                namespace=METRICS_NAMESPACE,
                metric_name="Errors",
                dimensions_map={"ToolName": name},
                statistic="Sum",
                label=name,
            )
            for name in TOOL_NAMES
        ]

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="ツール呼び出し回数",
                left=invocation_metrics,
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="ツールエラー数",
                left=error_metrics,
                width=12,
            ),
        )
