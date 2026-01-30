"""オッズ取得のテスト.

リアルタイムオッズ（jvd_o1テーブル）と確定オッズ（jvd_se.tansho_odds）の
取得ロジックをテストする。

Issue #172: 開催前レースのオッズが0になる問題の対応
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# pg8000 のモックを追加（Linuxテスト環境用）
mock_pg8000 = MagicMock()
sys.modules['pg8000'] = mock_pg8000

# テスト対象モジュールへのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_realtime_odds, get_runners_by_race


class TestGetRealtimeOdds:
    """get_realtime_odds関数の単体テスト.

    jvd_o1テーブルからリアルタイムオッズを取得する機能をテスト。
    """

    @patch("database.get_db")
    def test_jvd_o1テーブルからオッズを取得できる(self, mock_get_db):
        """jvd_o1テーブルが存在し、データがある場合にオッズを取得できる."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # jvd_o1からのオッズデータ
        mock_cursor.fetchall.return_value = [
            (1, 35, 1),   # 馬番1: オッズ3.5倍（10倍で格納）, 人気1
            (2, 58, 2),   # 馬番2: オッズ5.8倍, 人気2
            (3, 120, 3),  # 馬番3: オッズ12.0倍, 人気3
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_realtime_odds("20260105_09_01")

        assert result is not None
        assert len(result) == 3
        assert result[1] == {"odds": 3.5, "popularity": 1}
        assert result[2] == {"odds": 5.8, "popularity": 2}
        assert result[3] == {"odds": 12.0, "popularity": 3}

    @patch("database.get_db")
    def test_jvd_o1テーブルが空の場合Noneを返す(self, mock_get_db):
        """jvd_o1テーブルにデータがない場合はNoneを返す."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # データなし
        mock_cursor.fetchall.return_value = []

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_realtime_odds("20260105_09_01")

        assert result is None

    @patch("database.get_db")
    def test_jvd_o1テーブルが存在しない場合Noneを返す(self, mock_get_db):
        """jvd_o1テーブルが存在しない場合はNoneを返す（例外をキャッチ）."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # テーブルが存在しないエラー
        mock_cursor.execute.side_effect = Exception(
            'relation "jvd_o1" does not exist'
        )

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_realtime_odds("20260105_09_01")

        assert result is None

    @patch("database.get_db")
    def test_不正なrace_idの場合Noneを返す(self, mock_get_db):
        """race_idの形式が不正な場合はNoneを返す."""
        result = get_realtime_odds("invalid")

        assert result is None
        mock_get_db.assert_not_called()


class TestGetRunnersWithRealtimeOdds:
    """get_runners_by_race関数のリアルタイムオッズ統合テスト.

    確定オッズ（jvd_se）とリアルタイムオッズ（jvd_o1）の優先順位をテスト。
    """

    @patch("database.get_realtime_odds")
    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_リアルタイムオッズが優先される(
        self, mock_get_db, mock_fetch_all, mock_get_realtime_odds
    ):
        """jvd_o1のリアルタイムオッズがjvd_seの確定オッズより優先される."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # _fetch_all_as_dicts の戻り値（jvd_seからのデータ）
        mock_fetch_all.return_value = [
            {
                "umaban": "1",
                "wakuban": "1",
                "bamei": "テスト馬1",
                "ketto_toroku_bango": "2020100001",
                "kishumei_ryakusho": "テスト騎手",
                "kishu_code": "00001",
                "chokyoshimei_ryakusho": "テスト調教師",
                "futan_juryo": "550",
                "bataiju": "480",
                "zogen_sa": "+2",
                "tansho_odds": "",  # 確定オッズなし
                "tansho_ninkijun": "",
            },
        ]

        # リアルタイムオッズ
        mock_get_realtime_odds.return_value = {
            1: {"odds": 3.5, "popularity": 1},
        }

        result = get_runners_by_race("20260105_09_01")

        assert len(result) == 1
        assert result[0]["odds"] == 3.5
        assert result[0]["popularity"] == 1

    @patch("database.get_realtime_odds")
    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_リアルタイムオッズがない場合は確定オッズを使用(
        self, mock_get_db, mock_fetch_all, mock_get_realtime_odds
    ):
        """リアルタイムオッズがない場合は確定オッズ（jvd_se）を使用."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # _fetch_all_as_dicts の戻り値（確定オッズあり）
        mock_fetch_all.return_value = [
            {
                "umaban": "1",
                "wakuban": "1",
                "bamei": "テスト馬1",
                "ketto_toroku_bango": "2020100001",
                "kishumei_ryakusho": "テスト騎手",
                "kishu_code": "00001",
                "chokyoshimei_ryakusho": "テスト調教師",
                "futan_juryo": "550",
                "bataiju": "480",
                "zogen_sa": "+2",
                "tansho_odds": "35",  # 確定オッズ3.5倍
                "tansho_ninkijun": "1",
            },
        ]

        # リアルタイムオッズなし
        mock_get_realtime_odds.return_value = None

        result = get_runners_by_race("20260105_09_01")

        assert len(result) == 1
        assert result[0]["odds"] == 3.5
        assert result[0]["popularity"] == 1

    @patch("database.get_realtime_odds")
    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_両方のオッズがない場合はNoneを返す(
        self, mock_get_db, mock_fetch_all, mock_get_realtime_odds
    ):
        """リアルタイムオッズも確定オッズもない場合はodds=None."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # _fetch_all_as_dicts の戻り値（オッズなし）
        mock_fetch_all.return_value = [
            {
                "umaban": "1",
                "wakuban": "1",
                "bamei": "テスト馬1",
                "ketto_toroku_bango": "2020100001",
                "kishumei_ryakusho": "テスト騎手",
                "kishu_code": "00001",
                "chokyoshimei_ryakusho": "テスト調教師",
                "futan_juryo": "550",
                "bataiju": "480",
                "zogen_sa": "+2",
                "tansho_odds": "",
                "tansho_ninkijun": "",
            },
        ]

        # リアルタイムオッズなし
        mock_get_realtime_odds.return_value = None

        result = get_runners_by_race("20260105_09_01")

        assert len(result) == 1
        assert result[0]["odds"] is None
        assert result[0]["popularity"] is None
