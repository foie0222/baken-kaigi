"""統計関数のテスト.

get_jockey_course_stats と get_popularity_payout_stats の単体テスト。
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

from database import get_jockey_course_stats, get_popularity_payout_stats, get_past_race_statistics


class TestGetJockeyCourseStats:
    """get_jockey_course_stats関数の単体テスト."""

    @patch("database.get_db")
    def test_正常系_騎手成績を取得できる(self, mock_get_db):
        """正常なデータで騎手成績を取得できることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # 騎手名取得クエリの結果
        mock_cursor.fetchone.side_effect = [
            ("川田将雅",),  # 騎手名
            (50, 15, 30),  # 成績: total_rides, wins, places
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_jockey_course_stats(
            jockey_id="00001",
            track_code="1",
            distance=1600,
            keibajo_code="09",
            limit_races=100,
        )

        assert result is not None
        assert result["jockey_id"] == "00001"
        assert result["jockey_name"] == "川田将雅"
        assert result["total_rides"] == 50
        assert result["wins"] == 15
        assert result["places"] == 30
        assert result["win_rate"] == 30.0
        assert result["place_rate"] == 60.0

    @patch("database.get_db")
    def test_データが存在しない場合Noneを返す(self, mock_get_db):
        """騎手データが存在しない場合Noneを返すことを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # 騎手名取得
        mock_cursor.fetchone.side_effect = [
            ("不明騎手",),  # 騎手名
            (0, 0, 0),  # 成績なし
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_jockey_course_stats(
            jockey_id="99999",
            track_code="1",
            distance=1600,
        )

        assert result is None

    @patch("database.get_db")
    def test_競馬場指定なしでも取得できる(self, mock_get_db):
        """競馬場コードを指定しない場合でも正常に取得できることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            ("テスト騎手",),
            (100, 20, 50),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_jockey_course_stats(
            jockey_id="00002",
            track_code="2",
            distance=1200,
            keibajo_code=None,  # 競馬場指定なし
        )

        assert result is not None
        assert result["conditions"]["keibajo_code"] is None

    @patch("database.get_db")
    def test_DBエラー時はNoneを返す(self, mock_get_db):
        """データベースエラー時にNoneを返すことを確認."""
        mock_get_db.return_value.__enter__.side_effect = Exception("DB Connection Error")

        result = get_jockey_course_stats(
            jockey_id="00001",
            track_code="1",
            distance=1600,
        )

        assert result is None


class TestGetPopularityPayoutStats:
    """get_popularity_payout_stats関数の単体テスト."""

    @patch("database.get_db")
    def test_正常系_配当統計を取得できる(self, mock_get_db):
        """正常なデータで配当統計を取得できることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # 統計クエリの結果
        # total_races, win_count, place_count, avg_win_payout, avg_place_payout
        mock_cursor.fetchone.return_value = (100, 33, 60, 238.5, 128.0)

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_popularity_payout_stats(
            track_code="1",
            distance=1600,
            popularity=1,
            limit_races=100,
        )

        assert result is not None
        assert result["popularity"] == 1
        assert result["total_races"] == 100
        assert result["win_count"] == 33
        assert result["avg_win_payout"] == 238.5
        assert result["avg_place_payout"] == 128.0
        # 回収率: 勝率(0.33) × 平均配当(238.5) = 78.7
        assert result["estimated_roi_win"] == pytest.approx(78.7, rel=0.1)

    @patch("database.get_db")
    def test_データが存在しない場合Noneを返す(self, mock_get_db):
        """統計データが存在しない場合Noneを返すことを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (0, 0, 0, None, None)

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_popularity_payout_stats(
            track_code="1",
            distance=9999,  # 存在しない距離
            popularity=1,
        )

        assert result is None

    @patch("database.get_db")
    def test_配当がNullの場合も処理できる(self, mock_get_db):
        """平均配当がNullの場合でも正常に処理できることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (50, 5, 15, None, None)

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_popularity_payout_stats(
            track_code="2",
            distance=1200,
            popularity=10,
        )

        assert result is not None
        assert result["avg_win_payout"] is None
        assert result["avg_place_payout"] is None
        assert result["estimated_roi_win"] == 0.0
        assert result["estimated_roi_place"] == 0.0

    @patch("database.get_db")
    def test_DBエラー時はNoneを返す(self, mock_get_db):
        """データベースエラー時にNoneを返すことを確認."""
        mock_get_db.return_value.__enter__.side_effect = Exception("DB Connection Error")

        result = get_popularity_payout_stats(
            track_code="1",
            distance=1600,
            popularity=1,
        )

        assert result is None

    @patch("database.get_db")
    def test_limit_racesパラメータがクエリに渡される(self, mock_get_db):
        """limit_racesパラメータが正しくクエリに渡されることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (50, 10, 25, 200.0, 120.0)

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_popularity_payout_stats(
            track_code="1",
            distance=1600,
            popularity=2,
            limit_races=200,
        )

        # executeが呼ばれたことを確認
        mock_cursor.execute.assert_called_once()
        # パラメータにlimit_racesが含まれていることを確認
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert 200 in params  # limit_racesの値


class TestGetPastRaceStats:
    """get_past_race_statistics関数の単体テスト（平均配当機能）."""

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_正常系_平均配当を取得できる(self, mock_get_db, mock_fetch_dicts):
        """正常なデータで平均配当を取得できることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # レース一覧クエリの結果
        races = [
            ("2026", "0131", "05", "01"),
            ("2026", "0131", "05", "02"),
        ]

        # 人気別統計クエリの結果
        popularity_rows = [
            {"popularity": "1", "total_runs": 100, "wins": 33, "places": 60},
            {"popularity": "2", "total_runs": 100, "wins": 20, "places": 50},
        ]

        # 平均配当クエリの結果
        avg_payouts = (238.5, 128.0)

        mock_cursor.fetchall.return_value = races
        mock_fetch_dicts.return_value = popularity_rows
        mock_cursor.fetchone.return_value = avg_payouts

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_past_race_statistics(
            track_code="1",
            distance=1600,
            grade_code=None,
            limit_races=100,
        )

        assert result is not None
        assert result["total_races"] == 2
        assert result["avg_win_payout"] == 238.5
        assert result["avg_place_payout"] == 128.0

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_配当データがない場合Noneを返す(self, mock_get_db, mock_fetch_dicts):
        """配当データが取得できない場合もNoneでなく適切に処理することを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # レース一覧
        races = [("2026", "0131", "05", "01")]

        # 人気別統計
        popularity_rows = [
            {"popularity": "1", "total_runs": 50, "wins": 15, "places": 30},
        ]

        # 平均配当がNone
        avg_payouts = (None, None)

        mock_cursor.fetchall.return_value = races
        mock_fetch_dicts.return_value = popularity_rows
        mock_cursor.fetchone.return_value = avg_payouts

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_past_race_statistics(
            track_code="1",
            distance=1600,
        )

        assert result is not None
        assert result["avg_win_payout"] is None
        assert result["avg_place_payout"] is None

    @patch("database.get_db")
    def test_レースが存在しない場合Noneを返す(self, mock_get_db):
        """該当レースが存在しない場合Noneを返すことを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = []

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_past_race_statistics(
            track_code="1",
            distance=9999,  # 存在しない距離
        )

        assert result is None
