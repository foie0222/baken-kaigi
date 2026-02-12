"""コース適性エンドポイントのテスト.

GET /horses/{horse_id}/course-aptitude の単体テスト。
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
    get_horse_course_aptitude,
    _classify_distance,
    _classify_gate,
)


class TestClassifyDistance:
    """_classify_distance関数のテスト."""

    def test_短距離_1200m(self):
        assert _classify_distance(1200) == "短距離"

    def test_短距離_1400m(self):
        assert _classify_distance(1400) == "短距離"

    def test_マイル_1600m(self):
        assert _classify_distance(1600) == "マイル"

    def test_マイル_1800m(self):
        assert _classify_distance(1800) == "マイル"

    def test_中距離_2000m(self):
        assert _classify_distance(2000) == "中距離"

    def test_中距離_2200m(self):
        assert _classify_distance(2200) == "中距離"

    def test_長距離_2400m(self):
        assert _classify_distance(2400) == "長距離"

    def test_長距離_3600m(self):
        assert _classify_distance(3600) == "長距離"


class TestClassifyGate:
    """_classify_gate関数のテスト."""

    def test_内枠_1枠(self):
        assert _classify_gate(1) == "内枠"

    def test_内枠_2枠(self):
        assert _classify_gate(2) == "内枠"

    def test_中枠_3枠(self):
        assert _classify_gate(3) == "中枠"

    def test_中枠_6枠(self):
        assert _classify_gate(6) == "中枠"

    def test_外枠_7枠(self):
        assert _classify_gate(7) == "外枠"

    def test_外枠_8枠(self):
        assert _classify_gate(8) == "外枠"


class TestGetHorseCourseAptitude:
    """get_horse_course_aptitude関数の単体テスト."""

    @patch("database.get_db")
    def test_正常系_コース適性データを取得できる(self, mock_get_db):
        """複数レースの出走結果からコース適性を集計できることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # 馬名取得 → 出走結果取得
        mock_cursor.fetchone.return_value = ("テスト馬",)
        mock_cursor.description = [
            ("keibajo_code",), ("track_code",), ("kyori",),
            ("babajotai_code_shiba",), ("babajotai_code_dirt",),
            ("wakuban",), ("kakutei_chakujun",), ("run_time",),
        ]
        mock_cursor.fetchall.return_value = [
            # 行タプル: description に従って辞書化される
            ("09", "11", "1600", "1", "", "3", "1", "01361"),
            ("09", "11", "1600", "1", "", "5", "3", "01365"),
            ("05", "21", "1800", "", "1", "7", "2", "01492"),
            ("05", "21", "1800", "", "2", "1", "5", "01510"),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_horse_course_aptitude("2021100001")

        assert result is not None
        assert result["horse_id"] == "2021100001"
        assert result["horse_name"] == "テスト馬"

        # by_venue: 阪神2走、東京2走
        assert len(result["by_venue"]) == 2
        hanshin = next(v for v in result["by_venue"] if v["venue"] == "阪神")
        assert hanshin["starts"] == 2
        assert hanshin["wins"] == 1
        assert hanshin["places"] == 2

        # by_track_type
        assert len(result["by_track_type"]) == 2
        turf = next(t for t in result["by_track_type"] if t["track_type"] == "芝")
        assert turf["starts"] == 2
        assert turf["wins"] == 1

        # by_distance
        mile = next(d for d in result["by_distance"] if d["distance_range"] == "マイル")
        assert mile["starts"] == 4
        assert mile["wins"] == 1

        # aptitude_summary
        summary = result["aptitude_summary"]
        assert summary["best_venue"] == "阪神"

    @patch("database.get_db")
    def test_データが存在しない場合Noneを返す(self, mock_get_db):
        """出走結果がない馬はNoneを返すことを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = [
            ("keibajo_code",), ("track_code",), ("kyori",),
            ("babajotai_code_shiba",), ("babajotai_code_dirt",),
            ("wakuban",), ("kakutei_chakujun",), ("run_time",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_horse_course_aptitude("9999999999")

        assert result is None

    @patch("database.get_db")
    def test_DBエラー時はNoneを返す(self, mock_get_db):
        """データベースエラー時にNoneを返すことを確認."""
        mock_get_db.return_value.__enter__.side_effect = Exception("DB Connection Error")

        result = get_horse_course_aptitude("2021100001")

        assert result is None

    @patch("database.get_db")
    def test_勝利なしの場合aptitude_summaryがNullになる(self, mock_get_db):
        """全レースで勝利なしの場合、サマリーがNoneになることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = ("未勝利馬",)
        mock_cursor.description = [
            ("keibajo_code",), ("track_code",), ("kyori",),
            ("babajotai_code_shiba",), ("babajotai_code_dirt",),
            ("wakuban",), ("kakutei_chakujun",), ("run_time",),
        ]
        # 全て4着以下
        mock_cursor.fetchall.return_value = [
            ("09", "11", "1600", "1", "", "3", "5", "01400"),
            ("05", "11", "2000", "1", "", "5", "8", "02050"),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_horse_course_aptitude("2022200002")

        assert result is not None
        summary = result["aptitude_summary"]
        assert summary["best_venue"] is None
        assert summary["best_distance"] is None

    @patch("database.get_db")
    def test_馬場状態コードが正しく変換される(self, mock_get_db):
        """芝コースの馬場状態が正しくカテゴリ化されることを確認."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = ("テスト馬2",)
        mock_cursor.description = [
            ("keibajo_code",), ("track_code",), ("kyori",),
            ("babajotai_code_shiba",), ("babajotai_code_dirt",),
            ("wakuban",), ("kakutei_chakujun",), ("run_time",),
        ]
        mock_cursor.fetchall.return_value = [
            ("09", "11", "2000", "1", "", "3", "1", "02001"),  # 良
            ("09", "11", "2000", "3", "", "3", "2", "02010"),  # 重
            ("09", "11", "2000", "4", "", "3", "3", "02020"),  # 不良
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_horse_course_aptitude("2022300003")

        conditions = {c["condition"]: c for c in result["by_track_condition"]}
        assert "良" in conditions
        assert "重" in conditions
        assert "不良" in conditions
        assert conditions["良"]["wins"] == 1


class TestCourseAptitudeEndpoint:
    """GET /horses/{horse_id}/course-aptitude エンドポイントのテスト."""

    @patch("database.get_db")
    def test_正常系_200レスポンス(self, mock_get_db):
        """正常なリクエストで200レスポンスを返すことを確認."""
        from fastapi.testclient import TestClient
        from main import app

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = ("テスト馬",)
        mock_cursor.description = [
            ("keibajo_code",), ("track_code",), ("kyori",),
            ("babajotai_code_shiba",), ("babajotai_code_dirt",),
            ("wakuban",), ("kakutei_chakujun",), ("run_time",),
        ]
        mock_cursor.fetchall.return_value = [
            ("09", "11", "1600", "1", "", "3", "1", "01361"),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        client = TestClient(app)
        response = client.get("/horses/2021100001/course-aptitude")

        assert response.status_code == 200
        data = response.json()
        assert data["horse_id"] == "2021100001"
        assert "by_venue" in data
        assert "aptitude_summary" in data

    @patch("database.get_db")
    def test_存在しない馬で404レスポンス(self, mock_get_db):
        """存在しない馬IDで404レスポンスを返すことを確認."""
        from fastapi.testclient import TestClient
        from main import app

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = [
            ("keibajo_code",), ("track_code",), ("kyori",),
            ("babajotai_code_shiba",), ("babajotai_code_dirt",),
            ("wakuban",), ("kakutei_chakujun",), ("run_time",),
        ]

        mock_get_db.return_value.__enter__.return_value = mock_conn

        client = TestClient(app)
        response = client.get("/horses/9999999999/course-aptitude")

        assert response.status_code == 404
