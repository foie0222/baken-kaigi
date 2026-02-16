"""デイリースポーツ スピード指数スクレイピングのテスト."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.daily_speed_index_scraper import (
    SOURCE_NAME,
    parse_circled_number,
    normalize_fullwidth,
    find_date_page_url,
    parse_race_data,
    generate_race_id,
    save_indices,
    CIRCLED_NUMBER_MAP,
)
from batch.ai_shisu_scraper import VENUE_CODE_MAP

TEST_PARSER = "html.parser"


class TestSourceName:
    """SOURCE_NAME定数のテスト."""

    def test_SOURCE_NAMEが正しい(self):
        """正常系: SOURCE_NAMEが'daily-speed'."""
        assert SOURCE_NAME == "daily-speed"


class TestCircledNumberMap:
    """丸数字マップのテスト."""

    def test_全18個の丸数字がマッピング(self):
        """正常系: 1-18の丸数字がマッピングされている."""
        assert len(CIRCLED_NUMBER_MAP) == 18
        assert CIRCLED_NUMBER_MAP["\u2460"] == 1
        assert CIRCLED_NUMBER_MAP["\u2471"] == 18


class TestParseCircledNumber:
    """丸数字変換のテスト."""

    def test_丸数字を整数に変換(self):
        """正常系: 丸数字を正しく変換."""
        assert parse_circled_number("\u2460") == 1   # ①
        assert parse_circled_number("\u246a") == 11  # ⑪
        assert parse_circled_number("\u2471") == 18  # ⑱

    def test_変換できない文字は0を返す(self):
        """正常系: 丸数字でないテキストは0."""
        assert parse_circled_number("abc") == 0
        assert parse_circled_number("") == 0

    def test_前後に空白がある場合(self):
        """正常系: 前後に空白があっても正しく変換."""
        assert parse_circled_number("  \u2460  ") == 1


class TestNormalizeFullwidth:
    """全角→半角変換のテスト."""

    def test_全角数字を半角に変換(self):
        """正常系: 全角数字を半角に変換."""
        assert normalize_fullwidth("２月８日") == "2月8日"

    def test_半角はそのまま(self):
        """正常系: 半角テキストは変化しない."""
        assert normalize_fullwidth("2月8日") == "2月8日"


class TestFindDatePageUrl:
    """日付ページURL検索のテスト."""

    def test_対象日付のURLを取得(self):
        """正常系: 対象日のリンクを見つけてURLを返す."""
        html = """
        <html><body>
            <a href="/horse/speed/data/0013109970.shtml">２月８日（土曜日）</a>
            <a href="/horse/speed/data/0013109971.shtml">２月９日（日曜日）</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_date_page_url(soup, 2, 8)

        assert url == "/horse/speed/data/0013109970.shtml"

    def test_日付がない場合はNone(self):
        """正常系: 対象日付がない場合はNone."""
        html = """
        <html><body>
            <a href="/horse/speed/data/0013109970.shtml">２月１日（土曜日）</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_date_page_url(soup, 2, 8)

        assert url is None

    def test_半角日付でもマッチ(self):
        """正常系: 半角数字の日付でもマッチする."""
        html = """
        <html><body>
            <a href="/horse/speed/data/0013109970.shtml">2月8日（土）</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_date_page_url(soup, 2, 8)

        assert url == "/horse/speed/data/0013109970.shtml"

    def test_speed_data以外のリンクは無視(self):
        """正常系: /horse/speed/data/以外のリンクは無視."""
        html = """
        <html><body>
            <a href="/horse/other/0013109970.shtml">２月８日</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_date_page_url(soup, 2, 8)

        assert url is None


class TestParseRaceData:
    """レースデータパースのテスト."""

    def _make_race_row(self, date, venue, race_num, horse_data):
        """テスト用のレース行HTMLを生成.

        horse_data: [(circled_number_char, speed_index), ...]
        """
        tds = [
            f"<td>{date}</td>",
            f"<td>{venue}</td>",
            f"<td>{race_num}</td>",
            "<td>条件</td>",
            "<td>1600</td>",
            "<td>芝</td>",
            "<td>16</td>",
        ]
        for cn, si in horse_data:
            tds.append(f"<td>{cn}</td>")
            tds.append(f"<td>{si}</td>")
        # パディング（最大18頭=36セル）
        while len(tds) < 43:
            tds.append("<td></td>")
        return "<tr>" + "".join(tds) + "</tr>"

    def test_正常なレースデータを抽出(self):
        """正常系: テーブルからスピード指数を抽出."""
        header = "<tr><th>日付</th><th>場所</th><th>R</th>" + "<th>x</th>" * 40 + "</tr>"
        row1 = self._make_race_row("20260208", "東京", "11", [
            ("\u246c", "339"),  # ⑬ = 13番
            ("\u2464", "320"),  # ⑤ = 5番
            ("\u2460", "310"),  # ① = 1番
        ])

        html = f"<html><body><table>{header}{row1}</table></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_data(soup, "20260208")

        assert len(races) == 1
        assert races[0]["venue"] == "東京"
        assert races[0]["race_number"] == 11
        indices = races[0]["indices"]
        assert len(indices) == 3
        # スコア降順
        assert indices[0]["horse_number"] == 13
        assert indices[0]["speed_index"] == 339.0
        assert indices[0]["rank"] == 1

    def test_別日のデータは除外(self):
        """正常系: 対象日付以外の行は除外."""
        header = "<tr><th>x</th>" * 43 + "</tr>"
        row = self._make_race_row("20260207", "東京", "1", [("\u2460", "300")])
        html = f"<html><body><table>{header}{row}</table></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_data(soup, "20260208")

        assert races == []

    def test_地方競馬場は除外(self):
        """正常系: JRA以外の競馬場は除外."""
        header = "<tr><th>x</th>" * 43 + "</tr>"
        row = self._make_race_row("20260208", "大井", "1", [("\u2460", "300")])
        html = f"<html><body><table>{header}{row}</table></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_data(soup, "20260208")

        assert races == []

    def test_馬名は空文字(self):
        """正常系: daily.co.jpは馬名を提供しないため空文字."""
        header = "<tr><th>x</th>" * 43 + "</tr>"
        row = self._make_race_row("20260208", "東京", "1", [("\u2460", "300")])
        html = f"<html><body><table>{header}{row}</table></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_data(soup, "20260208")

        assert races[0]["indices"][0]["horse_name"] == ""

    def test_テーブルがない場合は空リスト(self):
        """正常系: テーブルがない場合は空リスト."""
        html = "<html><body><p>データなし</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_data(soup, "20260208")

        assert races == []


class TestGenerateRaceId:
    """race_id生成のテスト."""

    def test_正しい形式でrace_idを生成(self):
        """正常系: JRA-VANスタイルのrace_idを生成."""
        race_id = generate_race_id("20260208", "東京", 11)
        assert race_id == "202602080511"

    def test_レース番号が1桁でもゼロパディング(self):
        """正常系: レース番号が1桁でも2桁にゼロパディング."""
        race_id = generate_race_id("20260208", "小倉", 1)
        assert race_id == "202602081001"

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
            {"rank": 1, "speed_index": 339.0, "horse_number": 13, "horse_name": ""},
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
        assert item["source"] == "daily-speed"
        assert item["venue"] == "東京"
        assert item["indices"] == indices
        assert "ttl" in item
        expected_ttl = int((scraped_at + timedelta(days=7)).timestamp())
        assert item["ttl"] == expected_ttl


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch("batch.daily_speed_index_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.daily_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 24,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    @patch("batch.daily_speed_index_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.daily_speed_index_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch index page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500

    @patch("batch.daily_speed_index_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.daily_speed_index_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert "error" in result["body"]
