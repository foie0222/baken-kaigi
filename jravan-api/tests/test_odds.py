"""オッズ取得のテスト.

確定オッズ（jvd_se.tansho_odds）とオッズ履歴の取得ロジックをテストする。
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
    get_runners_by_race, get_odds_history,
    _parse_tansho_odds, _parse_fukusho_odds, _parse_happyo_timestamp,
)


class TestGetRunners:
    """get_runners_by_race関数のテスト.

    jvd_seの確定オッズから出走馬データを取得する。
    """

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_確定オッズがありjvd_o1がない場合は確定オッズを使う(
        self, mock_get_db, mock_fetch_all,
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_cursor.fetchone.return_value = None  # jvd_o1 なし

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
                "tansho_odds": "35",
                "tansho_ninkijun": "1",
            },
        ]

        result = get_runners_by_race("202601050901")

        assert len(result) == 1
        assert result[0]["odds"] == 3.5
        assert result[0]["popularity"] == 1

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_確定オッズもjvd_o1もない場合はNone(
        self, mock_get_db, mock_fetch_all,
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_cursor.fetchone.return_value = None  # jvd_o1 なし

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

        result = get_runners_by_race("202601050901")

        assert len(result) == 1
        assert result[0]["odds"] is None
        assert result[0]["popularity"] is None

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_jvd_o1のリアルタイムオッズが確定オッズより優先される(
        self, mock_get_db, mock_fetch_all,
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # jvd_o1: 馬1=5.0倍/人気2, 馬2=3.5倍/人気1
        mock_cursor.fetchone.return_value = ("0100500202003501",)

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
                "tansho_odds": "35",  # 確定: 3.5倍
                "tansho_ninkijun": "1",  # 確定: 人気1
            },
            {
                "umaban": "2",
                "wakuban": "2",
                "bamei": "テスト馬2",
                "ketto_toroku_bango": "2020100002",
                "kishumei_ryakusho": "テスト騎手2",
                "kishu_code": "00002",
                "chokyoshimei_ryakusho": "テスト調教師2",
                "futan_juryo": "560",
                "bataiju": "490",
                "zogen_sa": "-2",
                "tansho_odds": "58",  # 確定: 5.8倍
                "tansho_ninkijun": "2",  # 確定: 人気2
            },
        ]

        result = get_runners_by_race("202601050901")

        assert len(result) == 2
        # jvd_o1のオッズが優先される
        assert result[0]["odds"] == 5.0
        assert result[0]["popularity"] == 2
        assert result[1]["odds"] == 3.5
        assert result[1]["popularity"] == 1

    @patch("database._fetch_all_as_dicts")
    @patch("database.get_db")
    def test_確定オッズがなくjvd_o1にオッズがある場合(
        self, mock_get_db, mock_fetch_all,
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # jvd_o1: 馬1=3.5倍/人気1
        mock_cursor.fetchone.return_value = ("0100350102005802",)

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
            {
                "umaban": "2",
                "wakuban": "2",
                "bamei": "テスト馬2",
                "ketto_toroku_bango": "2020100002",
                "kishumei_ryakusho": "テスト騎手2",
                "kishu_code": "00002",
                "chokyoshimei_ryakusho": "テスト調教師2",
                "futan_juryo": "560",
                "bataiju": "490",
                "zogen_sa": "-2",
                "tansho_odds": "",
                "tansho_ninkijun": "",
            },
        ]

        result = get_runners_by_race("202601050901")

        assert len(result) == 2
        # jvd_o1からオッズが取得される
        assert result[0]["odds"] == 3.5
        assert result[0]["popularity"] == 1
        assert result[1]["odds"] == 5.8
        assert result[1]["popularity"] == 2


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

    @patch("database.datetime")
    def test_ゼロ埋めタイムスタンプはfallback(self, mock_datetime: MagicMock):
        """ゼロ埋めタイムスタンプの場合は datetime.now().isoformat() にフォールバックする."""
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2030-01-02T03:04:05"
        mock_datetime.now.return_value = mock_now

        result = _parse_happyo_timestamp("2026", "00000000")
        assert result == "2030-01-02T03:04:05"


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

        result = get_odds_history("202602090901")

        assert result is not None
        assert result["race_id"] == "202602090901"
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

        result = get_odds_history("202602090901")

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

        result = get_odds_history("202602090901")

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

        result = get_odds_history("202602090901")

        assert result is None

    def test_不正なrace_idの場合Noneを返す(self):
        """race_idの形式が不正な場合はNoneを返す."""
        result = get_odds_history("invalid")
        assert result is None
