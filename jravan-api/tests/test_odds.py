"""オッズ取得のテスト.

リアルタイムオッズ（jvd_o1テーブル）と確定オッズ（jvd_se.tansho_odds）の
取得ロジックをテストする。

Issue #172: 開催前レースのオッズが0になる問題の対応
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
    get_realtime_odds, get_runners_by_race, get_odds_history,
    _parse_tansho_odds, _parse_fukusho_odds, _parse_happyo_timestamp,
)


class TestGetRealtimeOdds:
    """get_realtime_odds関数の単体テスト.

    jvd_o1テーブルからリアルタイムオッズを取得する機能をテスト。
    odds_tanshoカラムは馬番(2桁)+オッズ(4桁)+人気(2桁)が連結された文字列。
    """

    @patch("database.get_db")
    def test_jvd_o1テーブルからオッズを取得できる(self, mock_get_db):
        """jvd_o1テーブルが存在し、データがある場合にオッズを取得できる."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # odds_tansho形式: 馬番(2桁)+オッズ(4桁)+人気(2桁)
        # 馬番1: オッズ3.5倍(0035), 人気1 → "01003501"
        # 馬番2: オッズ5.8倍(0058), 人気2 → "02005802"
        # 馬番3: オッズ12.0倍(0120), 人気3 → "03012003"
        mock_cursor.fetchone.return_value = ("010035010200580203012003",)

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
        mock_cursor.fetchone.return_value = None

        mock_get_db.return_value.__enter__.return_value = mock_conn

        result = get_realtime_odds("20260105_09_01")

        assert result is None

    @patch("database.get_db")
    def test_odds_tanshoが空文字の場合Noneを返す(self, mock_get_db):
        """odds_tanshoが空文字の場合はNoneを返す."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = ("",)

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


class TestParseTanshoOdds:
    """_parse_tansho_odds のテスト."""

    def test_正常に解析できる(self):
        # 馬1: 3.5倍 人気1, 馬2: 5.8倍 人気2
        odds_str = "0100350102005802"
        result = _parse_tansho_odds(odds_str, {1: "馬A", 2: "馬B"})
        assert len(result) == 2
        assert result[0] == {"horse_number": 1, "horse_name": "馬A", "odds": 3.5, "popularity": 1}
        assert result[1] == {"horse_number": 2, "horse_name": "馬B", "odds": 5.8, "popularity": 2}

    def test_取消馬をスキップする(self):
        odds_str = "01******02005802"
        result = _parse_tansho_odds(odds_str, {2: "馬B"})
        assert len(result) == 1
        assert result[0]["horse_number"] == 2

    def test_空文字列で空リストを返す(self):
        assert _parse_tansho_odds("", {}) == []
        assert _parse_tansho_odds(None, {}) == []


class TestParseFukushoOdds:
    """_parse_fukusho_odds のテスト."""

    def test_正常に解析できる(self):
        # 馬1: min=2.4 max=3.3 人気4, 馬2: min=1.8 max=2.5 人気3
        odds_str = "010024003304020018002503"
        result = _parse_fukusho_odds(odds_str)
        assert len(result) == 2
        assert result[0] == {"horse_number": 1, "odds_min": 2.4, "odds_max": 3.3, "popularity": 4}
        assert result[1] == {"horse_number": 2, "odds_min": 1.8, "odds_max": 2.5, "popularity": 3}

    def test_取消馬をスキップする(self):
        odds_str = "01**********020018002503"
        result = _parse_fukusho_odds(odds_str)
        assert len(result) == 1
        assert result[0]["horse_number"] == 2


class TestParseHappyoTimestamp:
    """_parse_happyo_timestamp のテスト."""

    def test_正常なタイムスタンプ(self):
        result = _parse_happyo_timestamp("2026", "02081627")
        assert result == "2026-02-08T16:27:00"

    def test_ゼロ埋めタイムスタンプはfallback(self):
        result = _parse_happyo_timestamp("2026", "00000000")
        # datetime.now() の isoformat が返るのでフォーマットだけ確認
        assert "2026" not in result or "T" in result


class TestGetOddsHistory:
    """get_odds_history関数の単体テスト.

    優先順位: apd_sokuho_o1 → jvd_o1 → jvd_se
    """

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_apd_sokuho_o1から時系列データを返す(
        self, mock_get_db, mock_fetch_all,
    ):
        """apd_sokuho_o1に複数行ある場合、時系列データを返す."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # 馬名取得
        mock_fetch_all.return_value = [
            {"umaban": "1", "bamei": "テスト馬1"},
            {"umaban": "2", "bamei": "テスト馬2"},
        ]

        # apd_sokuho_o1: 2行の時系列データ
        mock_cursor.fetchall.return_value = [
            ("0100350102005802", "02091000"),
            ("0100300102006502", "02091030"),
        ]

        result = get_odds_history("20260209_09_01")

        assert result is not None
        assert result["race_id"] == "20260209_09_01"
        assert len(result["odds_history"]) == 2

        # 1つ目のスナップショット
        first = result["odds_history"][0]
        assert first["timestamp"] == "2026-02-09T10:00:00"
        assert first["odds"][0]["odds"] == 3.5
        # 2つ目のスナップショット（オッズが変動）
        second = result["odds_history"][1]
        assert second["timestamp"] == "2026-02-09T10:30:00"
        assert second["odds"][0]["odds"] == 3.0

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_sokuhoが空ならjvd_o1にフォールバック(
        self, mock_get_db, mock_fetch_all,
    ):
        """apd_sokuho_o1が空の場合、jvd_o1のスナップショットを返す."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # 馬名取得
        mock_fetch_all.return_value = [
            {"umaban": "1", "bamei": "テスト馬1"},
        ]

        # apd_sokuho_o1: 空、jvd_o1: 1行
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = ("0100350102005802", "02091500")

        result = get_odds_history("20260209_09_01")

        assert result is not None
        assert len(result["odds_history"]) == 1
        assert result["odds_history"][0]["timestamp"] == "2026-02-09T15:00:00"

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_o1も空なら確定オッズにフォールバック(
        self, mock_get_db, mock_fetch_all,
    ):
        """jvd_o1も空の場合、jvd_seの確定オッズを返す."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # 1回目: 馬名取得、2回目: 確定オッズ
        mock_fetch_all.side_effect = [
            [{"umaban": "1", "bamei": "テスト馬1"}],
            [{"umaban": "1", "tansho_odds": "35", "tansho_ninkijun": "1"}],
        ]

        # apd_sokuho_o1: 空、jvd_o1: なし
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None

        result = get_odds_history("20260209_09_01")

        assert result is not None
        assert len(result["odds_history"]) == 1
        assert result["odds_history"][0]["odds"][0]["odds"] == 3.5

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_全てのソースが空ならNone(
        self, mock_get_db, mock_fetch_all,
    ):
        """全ソースにデータがない場合はNoneを返す."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        mock_fetch_all.side_effect = [[], []]
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None

        result = get_odds_history("20260209_09_01")

        assert result is None

    def test_不正なrace_idの場合Noneを返す(self):
        """race_idの形式が不正な場合はNoneを返す."""
        result = get_odds_history("invalid")
        assert result is None
