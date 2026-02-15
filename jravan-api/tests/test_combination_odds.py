"""連勝式オッズパーサーのテスト.

jvd_o2〜o6テーブルの連勝式オッズ解析と、
全券種一括取得（get_all_odds）をテストする。
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# テスト対象モジュールへのパスを追加（conftest.py で pg8000 モック済み）
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    _parse_combination_odds_2h,
    _parse_combination_odds_3h,
    _parse_wide_odds,
    get_all_odds,
)


class TestParseCombinationOdds2h:
    """_parse_combination_odds_2h のテスト.

    jvd_o2(馬連)/o3(ワイド)/o4(馬単) 用パーサー。
    13文字/組: kumiban(4) + odds(6, ÷10) + ninkijun(3)
    """

    def test_馬連オッズを正常に解析できる(self):
        # 1-2: 64.8倍 (648÷10) 人気5, 1-3: 155.2倍 (1552÷10) 人気12
        odds_str = "0102000648005" + "0103001552012"
        result = _parse_combination_odds_2h(odds_str)
        assert len(result) == 2
        assert result["1-2"] == 64.8
        assert result["1-3"] == 155.2

    def test_取消馬をスキップする(self):
        # 取消 + 正常: 1-3: 155.2倍
        odds_str = "0102******005" + "0103001552012"
        result = _parse_combination_odds_2h(odds_str)
        assert len(result) == 1
        assert result["1-3"] == 155.2

    def test_空文字列で空辞書を返す(self):
        assert _parse_combination_odds_2h("") == {}
        assert _parse_combination_odds_2h(None) == {}


class TestParseWideOdds:
    """_parse_wide_odds のテスト.

    jvd_o3(ワイド) 用パーサー。
    17文字/組: kumiban(4桁) + odds_min(5桁, ÷10) + odds_max(5桁, ÷10) + ninkijun(3桁)
    """

    def test_ワイドオッズを正常に解析できる(self):
        # 1-2: min=35.6 max=37.4 rank=30, 1-3: min=24.0 max=25.3 rank=24
        odds_str = "01020035600374030" + "01030024000253024"
        result = _parse_wide_odds(odds_str)
        assert len(result) == 2
        assert result["1-2"] == 35.6
        assert result["1-3"] == 24.0

    def test_複数エントリを正しく解析できる(self):
        # 実データから: 1-2, 1-3, 1-4 の3エントリ
        odds_str = "01020035600374030" + "01030024000253024" + "01040007900087013"
        result = _parse_wide_odds(odds_str)
        assert len(result) == 3
        assert result["1-2"] == 35.6
        assert result["1-3"] == 24.0
        assert result["1-4"] == 7.9

    def test_取消馬をスキップする(self):
        odds_str = "0102*************" + "01030024000253024"
        result = _parse_wide_odds(odds_str)
        assert len(result) == 1
        assert result["1-3"] == 24.0

    def test_空文字列で空辞書を返す(self):
        assert _parse_wide_odds("") == {}
        assert _parse_wide_odds(None) == {}


class TestParseCombinationOdds3h:
    """_parse_combination_odds_3h のテスト.

    jvd_o5(三連複)/o6(三連単) 用パーサー。
    15文字/組: kumiban(6) + odds(6, ÷10) + ninkijun(3)
    """

    def test_三連複オッズを正常に解析できる(self):
        # 1-2-3: 341.9倍 人気23, 1-2-4: 1205.0倍 人気45
        odds_str = "010203003419023" + "010204012050045"
        result = _parse_combination_odds_3h(odds_str)
        assert len(result) == 2
        assert result["1-2-3"] == 341.9
        assert result["1-2-4"] == 1205.0

    def test_取消馬をスキップする(self):
        # 取消 + 正常
        odds_str = "010203*********" + "010204012050045"
        result = _parse_combination_odds_3h(odds_str)
        assert len(result) == 1
        assert result["1-2-4"] == 1205.0

    def test_空文字列で空辞書を返す(self):
        assert _parse_combination_odds_3h("") == {}
        assert _parse_combination_odds_3h(None) == {}


class TestGetAllOdds:
    """get_all_odds のテスト."""

    @patch("database.get_db")
    def test_全券種のオッズを一括取得できる(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # 6テーブル分の fetchone を順番に返す
        # jvd_o1: odds_tansho, odds_fukusho
        # jvd_o2: odds_umaren
        # jvd_o3: odds_wide
        # jvd_o4: odds_umatan
        # jvd_o5: odds_sanrenpuku
        # jvd_o6: odds_sanrentan
        mock_cursor.fetchone.side_effect = [
            ("010035010200580203012003", "010024003304020018002503"),  # o1: tansho + fukusho
            ("0102000648005",),   # o2: umaren 64.8倍
            ("01020012300155030",),  # o3: wide min=12.3 max=15.5 rank=30
            ("0102001285005",),   # o4: umatan 128.5倍
            ("010203003419023",), # o5: sanrenpuku
            ("010203020483023",), # o6: sanrentan 2048.3倍
        ]

        result = get_all_odds("20260215_06_11")

        assert result is not None
        # 単勝
        assert result["win"]["1"] == 3.5
        assert result["win"]["2"] == 5.8
        # 複勝
        assert result["place"]["1"]["min"] == 2.4
        assert result["place"]["1"]["max"] == 3.3
        # 馬連
        assert result["quinella"]["1-2"] == 64.8
        # ワイド
        assert result["quinella_place"]["1-2"] == 12.3
        # 馬単
        assert result["exacta"]["1-2"] == 128.5
        # 三連複
        assert result["trio"]["1-2-3"] == 341.9
        # 三連単
        assert result["trifecta"]["1-2-3"] == 2048.3

    @patch("database.get_db")
    def test_一部テーブルが空でも他券種は取得できる(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # o1 にだけデータあり、他は空
        mock_cursor.fetchone.side_effect = [
            ("010035010200580203012003", "010024003304020018002503"),  # o1
            (None,),  # o2
            (None,),  # o3
            (None,),  # o4
            (None,),  # o5
            (None,),  # o6
        ]

        result = get_all_odds("20260215_06_11")

        assert result is not None
        assert result["win"]["1"] == 3.5
        assert result["quinella"] == {}
        assert result["trio"] == {}

    @patch("database.get_db")
    def test_全テーブルが空ならNoneを返す(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = mock_conn

        # 全テーブル空
        mock_cursor.fetchone.side_effect = [
            (None, None),  # o1
            (None,),  # o2
            (None,),  # o3
            (None,),  # o4
            (None,),  # o5
            (None,),  # o6
        ]

        result = get_all_odds("20260215_06_11")

        assert result is None
