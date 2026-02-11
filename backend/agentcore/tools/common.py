"""AgentCoreツール共通モジュール.

エラーハンドリング、構造化ロギング、実行時間計測のデコレータを提供する。
"""

import logging
import time
from functools import wraps


def get_tool_logger(name: str) -> logging.Logger:
    """構造化ロガーを取得する.

    Args:
        name: ロガー名（通常はツールのモジュール名）

    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(f"agentcore.tools.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def handle_tool_errors(func):
    """ツールのエラーハンドリングデコレータ.

    予期しない例外をキャッチし、構造化されたエラーレスポンスを返す。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_tool_logger(func.__module__.split(".")[-1])
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {e}")
            return {"error": f"ツールの実行中にエラーが発生しました: {type(e).__name__}"}
    return wrapper


def log_tool_execution(func):
    """ツール実行時間の計測・ログデコレータ.

    ツールの呼び出しと完了をログに記録し、実行時間を計測する。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_tool_logger(func.__module__.split(".")[-1])
        logger.info(f"Tool invoked: {func.__name__}")
        start = time.time()
        result = func(*args, **kwargs)
        duration_ms = (time.time() - start) * 1000
        logger.info(f"Tool completed: {func.__name__} ({duration_ms:.0f}ms)")
        return result
    return wrapper
