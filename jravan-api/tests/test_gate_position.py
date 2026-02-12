"""枠順傾向エンドポイントのテスト.

GET /statistics/gate-position の単体テスト。
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# pg8000 のモックを追加（Linuxテスト環境用）
mock_pg8000 = MagicMock()
sys.modules['pg8000'] = mock_pg8000

# テスト対象モジュールへのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    get_gate_position_stats,
    VENUE_NAME_TO_CODE,
    TRACK_CONDITION_CODE_MAP,
)


class TestVenueNameToCode:
    """VENUE_NAME_TO_CODE逆引きマッピングのテスト."""

    def test_東京のコード変換(self):
        assert VENUE_NAME_TO_CODE["東京"] == "05"

    def test_阪神のコード変換(self):
        assert VENUE_NAME_TO_CODE["阪神"] == "09"

    def test_全10場が登録されている(self):
        assert len(VENUE_NAME_TO_CODE) == 10


class TestTrackConditionCodeMap:
    """TRACK_CONDITION_CODE_MAP のテスト."""

    def test_良は1(self):
        assert TRACK_CONDITION_CODE_MAP["良"] == "1"

    def test_不良は4(self):
        assert TRACK_CONDITION_CODE_MAP["不良"] == "4"


class TestGetGatePositionStats:
    """get_gate_position_stats関数の単体テスト."""

    @patch("database.get_db")
    def test_正常系_枠順統計を取得できる(self, mock_get_db):
        """正常なデータで枠順統計を取得できることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # 1回目: レース取得クエリ
        races = [
            ("2026", "0125", "09", "01"),
            ("2026", "0125", "09", "02"),
        ]
        # 2回目: 出走結果取得クエリ
        result_rows = [
            ("1", "1", "1"),   # 1枠1番 1着
            ("2", "3", "2"),   # 2枠3番 2着
            ("3", "5", "3"),   # 3枠5番 3着
            ("4", "7", "5"),   # 4枠7番 5着
            ("1", "2", "3"),   # 1枠2番 3着
            ("5", "9", "1"),   # 5枠9番 1着
            ("7", "13", "4"),  # 7枠13番 4着
            ("8", "16", "8"),  # 8枠16番 8着
        ]

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_gate_position_stats(venue="阪神")

        assert result is not None
        assert result["conditions"]["venue"] == "阪神"
        assert result["total_races"] == 2

        # by_gate の確認
        assert len(result["by_gate"]) > 0
        gate_1 = next(g for g in result["by_gate"] if g["gate"] == 1)
        assert gate_1["starts"] == 2
        assert gate_1["wins"] == 1
        assert gate_1["places"] == 2
        assert gate_1["gate_range"] == "1-2枠"

        # by_horse_number の確認
        assert len(result["by_horse_number"]) > 0

        # analysis の確認
        assert "favorable_gates" in result["analysis"]
        assert "unfavorable_gates" in result["analysis"]
        assert "comment" in result["analysis"]

    @patch("database.get_db")
    def test_存在しない競馬場名でNoneを返す(self, mock_get_db):
        """存在しない競馬場名を指定した場合Noneを返すことを確認."""
        result = get_gate_position_stats(venue="存在しない競馬場")

        assert result is None
        # DBへのアクセスなし
        mock_get_db.assert_not_called()

    @patch("database.get_db")
    def test_レースが存在しない場合Noneを返す(self, mock_get_db):
        """条件に合うレースがない場合Noneを返すことを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = []  # レースなし

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_gate_position_stats(venue="東京", distance=9999)

        assert result is None

    @patch("database.get_db")
    def test_track_typeフィルタが適用される(self, mock_get_db):
        """track_typeを指定した場合にフィルタが適用されることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        races = [("2026", "0125", "05", "01")]
        result_rows = [("3", "5", "1")]

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_gate_position_stats(venue="東京", track_type="芝")

        assert result is not None
        assert result["conditions"]["track_type"] == "芝"

        # SQLにtrack_codeフィルタが含まれていることを確認
        call_args = mock_cursor.execute.call_args_list[0]
        sql = call_args[0][0]
        assert "track_code LIKE '1%'" in sql

    @patch("database.get_db")
    def test_distanceフィルタが適用される(self, mock_get_db):
        """distanceを指定した場合にフィルタが適用されることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        races = [("2026", "0125", "05", "01")]
        result_rows = [("3", "5", "1")]

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_gate_position_stats(venue="東京", distance=1600)

        assert result is not None
        assert result["conditions"]["distance"] == 1600

    @patch("database.get_db")
    def test_track_conditionフィルタが適用される(self, mock_get_db):
        """track_conditionを指定した場合にフィルタが適用されることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        races = [("2026", "0125", "09", "01")]
        result_rows = [("1", "1", "1")]

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_gate_position_stats(venue="阪神", track_condition="重")

        assert result is not None
        assert result["conditions"]["track_condition"] == "重"

    @patch("database.get_db")
    def test_limitパラメータが適用される(self, mock_get_db):
        """limitを指定した場合にLIMIT句が適用されることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        races = [("2026", "0125", "05", "01")]
        result_rows = [("3", "5", "1")]

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_gate_position_stats(venue="東京", limit=50)

        assert result is not None
        # LIMIT句がSQL内に含まれることを確認
        call_args = mock_cursor.execute.call_args_list[0]
        sql = call_args[0][0]
        assert "LIMIT" in sql
        params = call_args[0][1]
        assert 50 in params

    @patch("database.get_db")
    def test_DBエラー時はNoneを返す(self, mock_get_db):
        """データベースエラー時にNoneを返すことを確認."""
        mock_get_db.return_value.__enter__.side_effect = Exception("DB Connection Error")

        result = get_gate_position_stats(venue="東京")

        assert result is None

    @patch("database.get_db")
    def test_有利不利枠の分析が正しい(self, mock_get_db):
        """平均勝率から5%以上離れた枠が有利/不利として判定されることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        races = [("2026", "0125", "09", str(i).zfill(2)) for i in range(1, 11)]

        # 1枠は勝率40%（高い）、8枠は勝率0%（低い）、それ以外は平均的
        result_rows = []
        # 1枠: 10走4勝
        for i in range(10):
            result_rows.append(("1", "1", "1" if i < 4 else "5"))
        # 2枠: 10走1勝
        for i in range(10):
            result_rows.append(("2", "3", "1" if i < 1 else "6"))
        # 3枠: 10走1勝
        for i in range(10):
            result_rows.append(("3", "5", "1" if i < 1 else "7"))
        # 8枠: 10走0勝
        for i in range(10):
            result_rows.append(("8", "16", "8"))

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_gate_position_stats(venue="阪神")

        assert result is not None
        # 平均勝率 = 6/40 = 15%
        # 1枠: 40% → 15%+5%=20%以上 → 有利
        assert 1 in result["analysis"]["favorable_gates"]
        # 8枠: 0% → 15%-5%=10%以下 → 不利
        assert 8 in result["analysis"]["unfavorable_gates"]

    @patch("database.get_db")
    def test_差がない場合のコメント(self, mock_get_db):
        """全枠の勝率が近い場合、差が小さいコメントが生成されることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        races = [("2026", "0125", "09", "01")]
        # 各枠1走1勝（全て均等）
        result_rows = [
            ("1", "1", "1"),
            ("2", "3", "1"),
            ("3", "5", "1"),
            ("4", "7", "1"),
        ]

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_gate_position_stats(venue="阪神")

        assert result is not None
        assert result["analysis"]["comment"] == "枠順による有利不利の差は小さい"


class TestGatePositionEndpoint:
    """GET /statistics/gate-position エンドポイントのテスト."""

    @patch("database.get_db")
    def test_正常系_200レスポンス(self, mock_get_db):
        """正常なリクエストで200レスポンスを返すことを確認."""
        from fastapi.testclient import TestClient
        from main import app

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        races = [("2026", "0125", "05", "01")]
        result_rows = [("3", "5", "1")]

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        client = TestClient(app)
        response = client.get("/statistics/gate-position?venue=東京")

        assert response.status_code == 200
        data = response.json()
        assert data["conditions"]["venue"] == "東京"
        assert "by_gate" in data
        assert "analysis" in data

    @patch("database.get_db")
    def test_venueパラメータ必須(self, mock_get_db):
        """venueパラメータなしで422レスポンスを返すことを確認."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.get("/statistics/gate-position")

        assert response.status_code == 422

    @patch("database.get_db")
    def test_存在しない競馬場で404レスポンス(self, mock_get_db):
        """存在しない競馬場名で404レスポンスを返すことを確認."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.get("/statistics/gate-position?venue=存在しない")

        assert response.status_code == 404

    @patch("database.get_db")
    def test_全パラメータ指定_200レスポンス(self, mock_get_db):
        """全パラメータを指定して200レスポンスを返すことを確認."""
        from fastapi.testclient import TestClient
        from main import app

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        races = [("2026", "0125", "09", "01")]
        result_rows = [("1", "1", "1")]

        mock_cursor.fetchall.side_effect = [races, result_rows]
        mock_cursor.description = [
            ("wakuban",), ("umaban",), ("kakutei_chakujun",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        client = TestClient(app)
        response = client.get(
            "/statistics/gate-position"
            "?venue=阪神&track_type=芝&distance=1600&track_condition=良&limit=100"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conditions"]["venue"] == "阪神"
        assert data["conditions"]["track_type"] == "芝"
        assert data["conditions"]["distance"] == 1600
        assert data["conditions"]["track_condition"] == "良"
