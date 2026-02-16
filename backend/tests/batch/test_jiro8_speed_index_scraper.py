"""jiro8 スピード指数スクレイピングのテスト."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.jiro8_speed_index_scraper import (
    SOURCE_NAME,
    parse_race_page,
    generate_race_id,
    save_indices,
    VENUE_CODE_TO_NAME,
    JIRO8_VENUE_CODE_MAP,
)
from batch.ai_shisu_scraper import VENUE_CODE_MAP

TEST_PARSER = "html.parser"


class TestSourceName:
    """SOURCE_NAME定数のテスト."""

    def test_SOURCE_NAMEが正しい(self):
        """正常系: SOURCE_NAMEが'jiro8-speed'."""
        assert SOURCE_NAME == "jiro8-speed"


class TestVenueCodeMaps:
    """競馬場コードマップのテスト."""

    def test_全JRA競馬場がマッピングされている(self):
        """正常系: 10場すべてがマッピングされている."""
        assert len(JIRO8_VENUE_CODE_MAP) == 10
        assert JIRO8_VENUE_CODE_MAP["東京"] == "05"
        assert JIRO8_VENUE_CODE_MAP["京都"] == "08"

    def test_逆引きマップの整合性(self):
        """正常系: コード→名前の逆引きが正しい."""
        assert VENUE_CODE_TO_NAME["05"] == "東京"
        assert VENUE_CODE_TO_NAME["08"] == "京都"
        assert len(VENUE_CODE_TO_NAME) == 10


class TestParseRacePage:
    """レースページパースのテスト."""

    def _make_race_table_html(self, horse_numbers, speed_indices, horse_names=None):
        """テスト用の馬柱テーブルHTMLを生成."""
        rows = []
        # 30行以上のダミー行を作る（main_table判定用）
        for i in range(34):
            rows.append("<tr><td></td></tr>")

        # 馬番行（右→左に並ぶ = reverseして格納）
        hn_tds = "".join(f"<td>{hn}</td>" for hn in reversed(horse_numbers))
        rows[0] = f"<tr>{hn_tds}<td>馬番</td></tr>"

        # 馬名行
        if horse_names:
            name_tds = "".join(f"<td>{name}</td>" for name in reversed(horse_names))
            rows[1] = f"<tr>{name_tds}<td>馬名</td></tr>"

        # スピード指数行
        si_tds = "".join(f"<td>{si}</td>" for si in reversed(speed_indices))
        rows[33] = f"<tr>{si_tds}<td>スピード指数</td></tr>"

        return f"<html><body><table>{''.join(rows)}</table></body></html>"

    def test_正常なデータを抽出(self):
        """正常系: 馬柱テーブルからスピード指数を抽出."""
        html = self._make_race_table_html(
            horse_numbers=[1, 2, 3],
            speed_indices=[85.5, 90.2, 78.0],
            horse_names=["馬A/父A", "馬B/父B", "馬C/父C"],
        )
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_race_page(soup)

        assert len(results) == 3
        # スコア降順
        assert results[0]["horse_number"] == 2
        assert results[0]["speed_index"] == 90.2
        assert results[0]["rank"] == 1
        assert results[1]["horse_number"] == 1
        assert results[1]["speed_index"] == 85.5
        assert results[1]["rank"] == 2

    def test_馬名のスラッシュ区切り(self):
        """正常系: 馬名/父名の形式で馬名のみ抽出."""
        html = self._make_race_table_html(
            horse_numbers=[1],
            speed_indices=[85.0],
            horse_names=["テスト馬/父馬名"],
        )
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_race_page(soup)

        assert len(results) == 1
        assert results[0]["horse_name"] == "テスト馬"

    def test_指数が0以下の馬は除外(self):
        """正常系: スピード指数が0以下の馬は除外."""
        html = self._make_race_table_html(
            horse_numbers=[1, 2],
            speed_indices=[85.0, 0.0],
        )
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_race_page(soup)

        assert len(results) == 1
        assert results[0]["horse_number"] == 1

    def test_馬番が範囲外は除外(self):
        """正常系: 馬番が1-18以外は除外."""
        html = self._make_race_table_html(
            horse_numbers=[0, 5, 19],
            speed_indices=[80.0, 85.0, 90.0],
        )
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_race_page(soup)

        assert len(results) == 1
        assert results[0]["horse_number"] == 5

    def test_テーブルが見つからない場合(self):
        """正常系: 30行以上のテーブルがない場合は空リスト."""
        html = "<html><body><table><tr><td>短いテーブル</td></tr></table></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_race_page(soup)

        assert results == []

    def test_馬番行がない場合(self):
        """正常系: 馬番行やスピード指数行がない場合は空リスト."""
        rows = ["<tr><td></td></tr>" for _ in range(35)]
        html = f"<html><body><table>{''.join(rows)}</table></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_race_page(soup)

        assert results == []


class TestGenerateRaceId:
    """race_id生成のテスト."""

    def test_正しい形式でrace_idを生成(self):
        """正常系: JRA-VANスタイルのrace_idを生成."""
        race_id = generate_race_id("20260208", "東京", 11)
        assert race_id == "202602080511"

    def test_レース番号が1桁でもゼロパディング(self):
        """正常系: レース番号が1桁でも2桁にゼロパディング."""
        race_id = generate_race_id("20260208", "京都", 1)
        assert race_id == "202602080801"

    def test_すべての競馬場コード(self):
        """正常系: すべてのJRA競馬場でrace_idを生成."""
        for venue, code in VENUE_CODE_MAP.items():
            race_id = generate_race_id("20260208", venue, 12)
            assert race_id == f"20260208{code}12"


class TestSaveIndices:
    """DynamoDB保存のテスト."""

    def test_正常にDynamoDBに保存(self):
        """正常系: DynamoDBにスピード指数データを保存できる."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 6, 0, 0, tzinfo=JST)
        indices = [
            {"rank": 1, "speed_index": 90.2, "horse_number": 5, "horse_name": "馬A"},
        ]

        save_indices(
            table=mock_table,
            race_id="202602080511",
            venue="東京",
            race_number=11,
            indices=indices,
            scraped_at=scraped_at,
        )

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["race_id"] == "202602080511"
        assert item["source"] == "jiro8-speed"
        assert item["venue"] == "東京"
        assert item["race_number"] == 11
        assert len(item["indices"]) == 1
        assert "ttl" in item
        expected_ttl = int((scraped_at + timedelta(days=7)).timestamp())
        assert item["ttl"] == expected_ttl

    def test_scraped_atがISO形式で保存(self):
        """正常系: scraped_atがISO形式で保存される."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 21, 0, 0, tzinfo=JST)
        indices = [{"rank": 1, "speed_index": 90.2, "horse_number": 5, "horse_name": "馬A"}]

        save_indices(
            table=mock_table,
            race_id="202602080511",
            venue="東京",
            race_number=11,
            indices=indices,
            scraped_at=scraped_at,
        )

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["scraped_at"] == scraped_at.isoformat()


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch("batch.jiro8_speed_index_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.jiro8_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 36,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    @patch("batch.jiro8_speed_index_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.jiro8_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch top page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500

    @patch("batch.jiro8_speed_index_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.jiro8_speed_index_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert "error" in result["body"]

    @patch("batch.jiro8_speed_index_scraper.scrape_races")
    def test_offset_days_0を渡すと当日分を取得(self, mock_scrape_races):
        """正常系: offset_days=0 でscrape_racesに0を渡す."""
        from batch.jiro8_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 0}, None)

        mock_scrape_races.assert_called_once_with(offset_days=0)

    @patch("batch.jiro8_speed_index_scraper.scrape_races")
    def test_offset_days_1を渡すと翌日分を取得(self, mock_scrape_races):
        """正常系: offset_days=1 でscrape_racesに1を渡す."""
        from batch.jiro8_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 1}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.jiro8_speed_index_scraper.scrape_races")
    def test_offset_days省略時はデフォルト1(self, mock_scrape_races):
        """正常系: offset_daysが省略された場合はデフォルト1."""
        from batch.jiro8_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.jiro8_speed_index_scraper.scrape_races")
    def test_offset_days不正値はデフォルト1にフォールバック(self, mock_scrape_races):
        """正常系: offset_daysが不正値の場合はデフォルト1."""
        from batch.jiro8_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 5}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.jiro8_speed_index_scraper.scrape_races")
    def test_offset_days文字列はデフォルト1にフォールバック(self, mock_scrape_races):
        """正常系: offset_daysが文字列の場合はデフォルト1."""
        from batch.jiro8_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": "invalid"}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)
