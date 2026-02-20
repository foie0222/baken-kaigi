"""Orchestrator Lambda ハンドラのテスト."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from batch.auto_bet_orchestrator import (
    _schedule_name,
    handler,
)


class TestScheduleName:
    def test_race_idからスケジュール名を生成(self):
        assert _schedule_name("202602210501") == "auto-bet-202602210501"


class TestHandler:
    @patch("batch.auto_bet_orchestrator._create_schedule")
    @patch("batch.auto_bet_orchestrator._schedule_exists")
    @patch("batch.auto_bet_orchestrator._get_today_races")
    @patch("batch.auto_bet_orchestrator.datetime")
    def test_未スケジュールのレースにスケジュール作成(
        self, mock_dt, mock_races, mock_exists, mock_create
    ):
        now = datetime(2026, 2, 21, 0, 15, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_races.return_value = [
            {"race_id": "202602210501", "start_time": "2026-02-21T10:00:00+09:00"},
            {"race_id": "202602210502", "start_time": "2026-02-21T10:30:00+09:00"},
        ]
        mock_exists.return_value = False

        result = handler({}, None)
        assert result["created"] == 2
        assert mock_create.call_count == 2

    @patch("batch.auto_bet_orchestrator._create_schedule")
    @patch("batch.auto_bet_orchestrator._schedule_exists")
    @patch("batch.auto_bet_orchestrator._get_today_races")
    @patch("batch.auto_bet_orchestrator.datetime")
    def test_既存スケジュールはスキップ(
        self, mock_dt, mock_races, mock_exists, mock_create
    ):
        now = datetime(2026, 2, 21, 0, 15, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_races.return_value = [
            {"race_id": "202602210501", "start_time": "2026-02-21T10:00:00+09:00"},
        ]
        mock_exists.return_value = True

        result = handler({}, None)
        assert result["created"] == 0
        assert result["skipped"] == 1
        mock_create.assert_not_called()

    @patch("batch.auto_bet_orchestrator._create_schedule")
    @patch("batch.auto_bet_orchestrator._schedule_exists")
    @patch("batch.auto_bet_orchestrator._get_today_races")
    @patch("batch.auto_bet_orchestrator.datetime")
    def test_過去のレースはスキップ(
        self, mock_dt, mock_races, mock_exists, mock_create
    ):
        # now is after the race fire_at time (10:00 - 5min = 09:55 JST = 00:55 UTC)
        now = datetime(2026, 2, 21, 1, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_races.return_value = [
            {"race_id": "202602210501", "start_time": "2026-02-21T10:00:00+09:00"},
        ]

        result = handler({}, None)
        assert result["created"] == 0
        assert result["skipped"] == 1
        mock_create.assert_not_called()

    @patch("batch.auto_bet_orchestrator._get_today_races")
    @patch("batch.auto_bet_orchestrator.datetime")
    def test_非開催日はスキップ(self, mock_dt, mock_races):
        now = datetime(2026, 2, 21, 0, 15, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_races.return_value = []

        result = handler({}, None)
        assert result["status"] == "ok"
        assert result["created"] == 0
