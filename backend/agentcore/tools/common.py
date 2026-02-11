"""AgentCoreツール共通モジュール.

エラーハンドリング、構造化ロギング、実行時間計測のデコレータを提供する。
"""

import logging
import time
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


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
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | dict:
        logger = get_tool_logger(func.__module__.split(".")[-1])
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {e}")
            return {"error": f"ツールの実行中にエラーが発生しました: {type(e).__name__}"}
    return wrapper


def log_tool_execution(func: Callable[P, R]) -> Callable[P, R]:
    """ツール実行時間の計測・ログデコレータ.

    ツールの呼び出しと完了をログに記録し、実行時間を計測する。
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger = get_tool_logger(func.__module__.split(".")[-1])
        logger.info(f"Tool invoked: {func.__name__}")
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"Tool completed: {func.__name__} ({duration_ms:.0f}ms)")
        return result
    return wrapper
