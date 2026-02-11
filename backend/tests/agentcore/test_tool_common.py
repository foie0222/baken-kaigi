"""共通ツールモジュールのテスト."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.common import get_tool_logger, handle_tool_errors, log_tool_execution


class TestGetToolLogger:
    """get_tool_logger のテスト."""

    def test_ロガー名にプレフィックスが付く(self):
        logger = get_tool_logger("test_module")
        assert logger.name == "agentcore.tools.test_module"

    def test_ロガーのレベルがINFOに設定される(self):
        logger = get_tool_logger("test_level")
        assert logger.level == logging.INFO

    def test_ハンドラーを直接追加しない(self):
        logger = get_tool_logger("test_no_handler")
        # ライブラリ側でハンドラーを追加しない（ルートロガーに委譲）
        initial_count = len(logger.handlers)
        get_tool_logger("test_no_handler")
        assert len(logger.handlers) == initial_count

    def test_異なる名前のロガーは別インスタンス(self):
        logger1 = get_tool_logger("module_a")
        logger2 = get_tool_logger("module_b")
        assert logger1.name != logger2.name


class TestHandleToolErrors:
    """handle_tool_errors デコレータのテスト."""

    def test_正常実行時はそのまま結果を返す(self):
        @handle_tool_errors
        def success_func():
            return {"result": "ok"}

        assert success_func() == {"result": "ok"}

    def test_例外発生時はエラーレスポンスを返す(self):
        @handle_tool_errors
        def failing_func():
            raise ValueError("test error")

        result = failing_func()
        assert "error" in result
        assert "ValueError" in result["error"]

    def test_関数名が保持される(self):
        @handle_tool_errors
        def my_function():
            return {}

        assert my_function.__name__ == "my_function"

    def test_引数が正しく渡される(self):
        @handle_tool_errors
        def add(a, b):
            return {"sum": a + b}

        assert add(1, 2) == {"sum": 3}

    def test_キーワード引数が正しく渡される(self):
        @handle_tool_errors
        def greet(name="world"):
            return {"greeting": f"hello {name}"}

        assert greet(name="test") == {"greeting": "hello test"}


class TestLogToolExecution:
    """log_tool_execution デコレータのテスト."""

    def test_正常実行時はそのまま結果を返す(self):
        @log_tool_execution
        def success_func():
            return {"result": "ok"}

        assert success_func() == {"result": "ok"}

    def test_関数名が保持される(self):
        @log_tool_execution
        def my_tool():
            return {}

        assert my_tool.__name__ == "my_tool"

    def test_引数が正しく渡される(self):
        @log_tool_execution
        def multiply(a, b):
            return {"product": a * b}

        assert multiply(3, 4) == {"product": 12}

    def test_実行ログが記録される(self, caplog):
        @log_tool_execution
        def logged_func():
            return {"done": True}

        with caplog.at_level(logging.INFO):
            result = logged_func()

        assert result == {"done": True}
        # ログメッセージに関数名が含まれている
        log_messages = [r.message for r in caplog.records]
        invoked = any("logged_func" in m and "invoked" in m for m in log_messages)
        completed = any("logged_func" in m and "completed" in m for m in log_messages)
        assert invoked, f"invoked ログが見つからない: {log_messages}"
        assert completed, f"completed ログが見つからない: {log_messages}"

    def test_実行時間がログに含まれる(self, caplog):
        @log_tool_execution
        def timed_func():
            return {}

        with caplog.at_level(logging.INFO):
            timed_func()

        log_messages = [r.message for r in caplog.records]
        completed_msg = [m for m in log_messages if "completed" in m]
        assert completed_msg, f"completed ログが見つからない: {log_messages}"
        assert "ms" in completed_msg[0], f"実行時間(ms)がログに含まれていない: {completed_msg[0]}"


class TestDecoratorsComposition:
    """デコレータの組み合わせテスト."""

    def test_handle_tool_errorsとlog_tool_executionの組み合わせ(self):
        @handle_tool_errors
        @log_tool_execution
        def combined_func(x):
            return {"value": x * 2}

        assert combined_func(5) == {"value": 10}

    def test_組み合わせ時に例外がキャッチされる(self):
        @handle_tool_errors
        @log_tool_execution
        def failing_combined():
            raise RuntimeError("combined error")

        result = failing_combined()
        assert "error" in result
        assert "RuntimeError" in result["error"]
