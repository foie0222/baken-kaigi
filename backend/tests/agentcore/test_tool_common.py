"""共通ツールモジュールのテスト."""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.common import (
    _emit_metrics,
    get_tool_logger,
    log_tool_execution,
)


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


class TestEmitMetrics:
    """_emit_metrics のテスト."""

    @patch("tools.common.METRICS_ENABLED", False)
    def test_METRICS_ENABLED_falseの場合はメトリクス送信しない(self):
        with patch("tools.common._get_cloudwatch_client") as mock_get_client:
            _emit_metrics("test_tool", 100.0, success=True)
            mock_get_client.assert_not_called()

    @patch("tools.common.METRICS_ENABLED", True)
    def test_METRICS_ENABLED_trueの場合はCloudWatchクライアントが呼ばれる(self):
        mock_client = MagicMock()
        with patch("tools.common._get_cloudwatch_client", return_value=mock_client):
            _emit_metrics("test_tool", 150.5, success=True)

        mock_client.put_metric_data.assert_called_once()
        call_kwargs = mock_client.put_metric_data.call_args[1]
        assert call_kwargs["Namespace"] == "BakenKaigi/AgentTools"
        metric_data = call_kwargs["MetricData"]
        assert len(metric_data) == 3

        # ExecutionTime
        assert metric_data[0]["MetricName"] == "ExecutionTime"
        assert metric_data[0]["Value"] == 150.5
        assert metric_data[0]["Dimensions"] == [{"Name": "ToolName", "Value": "test_tool"}]

        # Invocations
        assert metric_data[1]["MetricName"] == "Invocations"
        assert metric_data[1]["Value"] == 1

        # Errors（成功時は0）
        assert metric_data[2]["MetricName"] == "Errors"
        assert metric_data[2]["Value"] == 0

    @patch("tools.common.METRICS_ENABLED", True)
    def test_エラー時はErrors_1が送信される(self):
        mock_client = MagicMock()
        with patch("tools.common._get_cloudwatch_client", return_value=mock_client):
            _emit_metrics("test_tool", 50.0, success=False)

        metric_data = mock_client.put_metric_data.call_args[1]["MetricData"]
        errors_metric = metric_data[2]
        assert errors_metric["MetricName"] == "Errors"
        assert errors_metric["Value"] == 1

    @patch("tools.common.METRICS_ENABLED", True)
    def test_メトリクス送信失敗時も例外が発生しない(self):
        mock_client = MagicMock()
        mock_client.put_metric_data.side_effect = Exception("CloudWatch error")
        with patch("tools.common._get_cloudwatch_client", return_value=mock_client):
            # 例外が発生しないことを確認
            _emit_metrics("test_tool", 100.0, success=True)


class TestMetricsIntegration:
    """デコレータとメトリクス送信の統合テスト."""

    @patch("tools.common.METRICS_ENABLED", True)
    def test_log_tool_execution成功時にメトリクスが送信される(self):
        mock_client = MagicMock()
        with patch("tools.common._get_cloudwatch_client", return_value=mock_client):
            @log_tool_execution
            def my_tool():
                return {"result": "ok"}

            result = my_tool()

        assert result == {"result": "ok"}
        mock_client.put_metric_data.assert_called_once()
        metric_data = mock_client.put_metric_data.call_args[1]["MetricData"]
        assert metric_data[2]["Value"] == 0  # Errors = 0

    @patch("tools.common.METRICS_ENABLED", True)
    def test_log_tool_executionでerror結果時にErrors_1が送信される(self):
        mock_client = MagicMock()
        with patch("tools.common._get_cloudwatch_client", return_value=mock_client):
            @log_tool_execution
            def my_tool():
                return {"error": "something went wrong"}

            result = my_tool()

        assert result == {"error": "something went wrong"}
        metric_data = mock_client.put_metric_data.call_args[1]["MetricData"]
        assert metric_data[2]["Value"] == 1  # Errors = 1

    @patch("tools.common.METRICS_ENABLED", False)
    def test_METRICS_ENABLED_falseではデコレータからメトリクス送信されない(self):
        with patch("tools.common._get_cloudwatch_client") as mock_get_client:
            @log_tool_execution
            def my_tool():
                return {"result": "ok"}

            result = my_tool()

        assert result == {"result": "ok"}
        mock_get_client.assert_not_called()
