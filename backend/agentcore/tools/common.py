"""AgentCoreツール共通モジュール.

エラーハンドリング、構造化ロギング、実行時間計測、CloudWatchメトリクス送信のデコレータを提供する。
"""

import logging
import os
import time
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

import boto3

P = ParamSpec("P")
R = TypeVar("R")

METRICS_ENABLED = os.environ.get("EMIT_CLOUDWATCH_METRICS", "false").lower() == "true"
METRICS_NAMESPACE = "BakenKaigi/AgentTools"

# CloudWatchクライアント（遅延初期化）
_cloudwatch_client = None


def _get_cloudwatch_client():
    global _cloudwatch_client
    if _cloudwatch_client is None:
        _cloudwatch_client = boto3.client(
            "cloudwatch",
            region_name=os.environ.get("AWS_REGION", "ap-northeast-1"),
        )
    return _cloudwatch_client


def _emit_metrics(tool_name: str, duration_ms: float, success: bool) -> None:
    """CloudWatchにメトリクスを送信する（ベストエフォート）."""
    if not METRICS_ENABLED:
        return
    try:
        client = _get_cloudwatch_client()
        client.put_metric_data(
            Namespace=METRICS_NAMESPACE,
            MetricData=[
                {
                    "MetricName": "ExecutionTime",
                    "Dimensions": [{"Name": "ToolName", "Value": tool_name}],
                    "Value": duration_ms,
                    "Unit": "Milliseconds",
                },
                {
                    "MetricName": "Invocations",
                    "Dimensions": [{"Name": "ToolName", "Value": tool_name}],
                    "Value": 1,
                    "Unit": "Count",
                },
                {
                    "MetricName": "Errors",
                    "Dimensions": [{"Name": "ToolName", "Value": tool_name}],
                    "Value": 0 if success else 1,
                    "Unit": "Count",
                },
            ],
        )
    except Exception:
        pass  # メトリクス送信失敗はツール実行に影響させない


def get_tool_logger(name: str) -> logging.Logger:
    """構造化ロガーを取得する.

    ハンドラーは追加せず、ロガーのレベルのみ設定する。
    ログ出力先はルートロガーやアプリケーション側の設定に委譲する。

    Args:
        name: ロガー名（通常はツールのモジュール名）

    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(f"agentcore.tools.{name}")
    logger.setLevel(logging.INFO)
    return logger


def handle_tool_errors(func: Callable[P, R]) -> Callable[P, R | dict]:
    """ツールのエラーハンドリングデコレータ.

    予期しない例外をキャッチし、構造化されたエラーレスポンスを返す。
    エラー時はCloudWatchにエラーメトリクスを送信する。
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | dict:
        logger = get_tool_logger(func.__module__.split(".")[-1])
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {e}")
            _emit_metrics(func.__name__, 0, success=False)
            return {"error": f"ツールの実行中にエラーが発生しました: {type(e).__name__}"}
    return wrapper


def log_tool_execution(func: Callable[P, R]) -> Callable[P, R]:
    """ツール実行時間の計測・ログデコレータ.

    ツールの呼び出しと完了をログに記録し、実行時間を計測する。
    完了時にCloudWatchメトリクスを送信する。
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger = get_tool_logger(func.__module__.split(".")[-1])
        logger.info(f"Tool invoked: {func.__name__}")
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"Tool completed: {func.__name__} ({duration_ms:.0f}ms)")
        success = not (isinstance(result, dict) and "error" in result)
        _emit_metrics(func.__name__, duration_ms, success=success)
        return result
    return wrapper
