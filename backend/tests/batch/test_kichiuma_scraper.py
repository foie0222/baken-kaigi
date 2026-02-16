"""吉馬 スピード指数スクレイピングのテスト."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.kichiuma_scraper import (
    SOURCE_NAME,
    find_venues_from_top_page,
    parse_race_list,
    parse_speed_index_page,
    generate_race_id,
    save_indices,
    KICHIUMA_VENUE_ID_MAP,
    VENUE_NAME_TO_KICHIUMA_ID,
)
from batch.ai_shisu_scraper import VENUE_CODE_MAP

TEST_PARSER = "html.parser"


class TestSourceName:
    """SOURCE_NAME定数のテスト."""

    def test_SOURCE_NAMEが正しい(self):
        """正常系: SOURCE_NAMEが'kichiuma-speed'."""
        assert SOURCE_NAME == "kichiuma-speed"


class TestVenueMaps:
    """競馬場IDマップのテスト."""

    def test_全JRA競馬場がマッピングされている(self):
        """正常系: 10場すべてがマッピングされている."""
        assert len(KICHIUMA_VENUE_ID_MAP) == 10
        assert KICHIUMA_VENUE_ID_MAP["75"] == "東京"
        assert KICHIUMA_VENUE_ID_MAP["78"] == "京都"

    def test_逆引きマップの整合性(self):
        """正常系: 名前→IDの逆引きが正しい."""
        assert VENUE_NAME_TO_KICHIUMA_ID["東京"] == "75"
        assert VENUE_NAME_TO_KICHIUMA_ID["京都"] == "78"


class TestFindVenuesFromTopPage:
    """トップページからの競馬場検索のテスト."""

    def test_対象日付の競馬場を取得(self):
        """正常系: リンクから開催競馬場を取得できる."""
        html = """
        <html><body>
            <td>2/8
                <a href="search.php?date=2026%2F2%2F8&id=75">東京</a>
                <a href="search.php?date=2026%2F2%2F8&id=78">京都</a>
            </td>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        venues = find_venues_from_top_page(soup)

        assert len(venues) == 2
        venue_names = [v["venue"] for v in venues]
        assert "東京" in venue_names
        assert "京都" in venue_names

    def test_地方競馬場は除外(self):
        """正常系: KICHIUMA_VENUE_ID_MAPにないIDは除外."""
        html = """
        <html><body>
            <td>2/8
                <a href="search.php?date=2026%2F2%2F8&id=75">東京</a>
                <a href="search.php?date=2026%2F2%2F8&id=99">大井</a>
            </td>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        venues = find_venues_from_top_page(soup)

        assert len(venues) == 1
        assert venues[0]["venue"] == "東京"

    def test_リンクがない場合は空リスト(self):
        """正常系: search.phpリンクがない場合は空リスト."""
        html = "<html><body><p>データなし</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        venues = find_venues_from_top_page(soup)

        assert venues == []

    def test_重複する競馬場は除外(self):
        """正常系: 同じ競馬場IDの重複は除外."""
        html = """
        <html><body>
            <td>2/8
                <a href="search.php?date=2026%2F2%2F8&id=75">東京1R</a>
                <a href="search.php?date=2026%2F2%2F8&id=75">東京2R</a>
            </td>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        venues = find_venues_from_top_page(soup)

        assert len(venues) == 1


class TestParseRaceList:
    """レース一覧パースのテスト."""

    def test_SPランクリンクを抽出(self):
        """正常系: p=lsリンクからレース一覧を抽出."""
        html = """
        <html><body>
            <a href="search.php?race_id=202602080175&date=2026%2F2%2F8&no=1&id=75&p=ls">SP1R</a>
            <a href="search.php?race_id=202602080175&date=2026%2F2%2F8&no=11&id=75&p=ls">SP11R</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list(soup, "75", "2026%2F2%2F8")

        assert len(races) == 2
        assert races[0]["race_number"] == 1
        assert races[1]["race_number"] == 11

    def test_p_lsリンクがない場合は空リスト(self):
        """正常系: SPランクリンクがない場合は空リスト."""
        html = """
        <html><body>
            <a href="search.php?race_id=xxx&date=yyy&no=1&id=75">出馬表</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list(soup, "75", "2026%2F2%2F8")

        assert races == []

    def test_race_idとnoがないリンクは除外(self):
        """正常系: race_idまたはnoがないp=lsリンクは除外."""
        html = """
        <html><body>
            <a href="search.php?p=ls">不完全</a>
            <a href="search.php?race_id=123&date=xxx&no=5&id=75&p=ls">完全</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list(soup, "75", "2026%2F2%2F8")

        assert len(races) == 1
        assert races[0]["race_number"] == 5


class TestParseSpeedIndexPage:
    """SPランクページパースのテスト."""

    def test_正常なデータを抽出(self):
        """正常系: SPランクテーブルからスピード指数を抽出."""
        html = """
        <html><body>
        <table>
            <tr><th>馬</th><th>前走Rnk</th><th>過去Rnk</th><th>競走馬名</th><th>前走</th><th>過去走</th></tr>
            <tr>
                <td>1</td><td>A</td><td>B</td><td>馬A</td><td>92.0</td><td>88.0</td><td>85.0</td><td>0</td><td>0</td>
            </tr>
            <tr>
                <td>5</td><td>C</td><td>D</td><td>馬B</td><td>88.5</td><td>86.0</td><td>84.0</td><td>0</td><td>0</td>
            </tr>
            <tr>
                <td>3</td><td>E</td><td>F</td><td>馬C</td><td>95.0</td><td>90.0</td><td>87.0</td><td>0</td><td>0</td>
            </tr>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_speed_index_page(soup)

        assert len(results) == 3
        # スコア降順
        assert results[0]["horse_number"] == 3
        assert results[0]["speed_index"] == 95.0
        assert results[0]["rank"] == 1
        assert results[0]["horse_name"] == "馬C"
        assert results[1]["horse_number"] == 1
        assert results[1]["rank"] == 2
        assert results[2]["horse_number"] == 5
        assert results[2]["rank"] == 3

    def test_指数が0以下の馬は除外(self):
        """正常系: スピード指数が0以下の馬は除外."""
        html = """
        <html><body>
        <table>
            <tr><th>馬</th><th>前走Rnk</th><th>過去Rnk</th><th>競走馬名</th><th>前走</th><th>過去走</th></tr>
            <tr><td>1</td><td>A</td><td>B</td><td>馬A</td><td>92.0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
            <tr><td>2</td><td>A</td><td>B</td><td>馬B</td><td>0.0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_speed_index_page(soup)

        assert len(results) == 1
        assert results[0]["horse_number"] == 1

    def test_テーブルが見つからない場合(self):
        """正常系: 該当テーブルがない場合は空リスト."""
        html = "<html><body><p>データなし</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_speed_index_page(soup)

        assert results == []

    def test_数値変換失敗行はスキップ(self):
        """正常系: 馬番や指数の変換に失敗した行はスキップ."""
        html = """
        <html><body>
        <table>
            <tr><th>馬</th><th>前走Rnk</th><th>過去Rnk</th><th>競走馬名</th><th>前走</th><th>過去走</th></tr>
            <tr><td>abc</td><td>A</td><td>B</td><td>馬X</td><td>92.0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
            <tr><td>5</td><td>A</td><td>B</td><td>馬Y</td><td>85.0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        results = parse_speed_index_page(soup)

        assert len(results) == 1
        assert results[0]["horse_name"] == "馬Y"


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
            {"rank": 1, "speed_index": 95.0, "horse_number": 3, "horse_name": "馬C"},
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
        assert item["source"] == "kichiuma-speed"
        assert item["venue"] == "東京"
        assert item["race_number"] == 11
        assert item["indices"] == indices
        assert "ttl" in item
        expected_ttl = int((scraped_at + timedelta(days=7)).timestamp())
        assert item["ttl"] == expected_ttl


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch("batch.kichiuma_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.kichiuma_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 24,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    @patch("batch.kichiuma_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.kichiuma_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch top page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500

    @patch("batch.kichiuma_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.kichiuma_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert "error" in result["body"]

    @patch("batch.kichiuma_scraper.scrape_races")
    def test_offset_days_0を渡すと当日分を取得(self, mock_scrape_races):
        """正常系: offset_days=0 でscrape_racesに0を渡す."""
        from batch.kichiuma_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 0}, None)

        mock_scrape_races.assert_called_once_with(offset_days=0)

    @patch("batch.kichiuma_scraper.scrape_races")
    def test_offset_days_1を渡すと翌日分を取得(self, mock_scrape_races):
        """正常系: offset_days=1 でscrape_racesに1を渡す."""
        from batch.kichiuma_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 1}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.kichiuma_scraper.scrape_races")
    def test_offset_days省略時はデフォルト1(self, mock_scrape_races):
        """正常系: offset_daysが省略された場合はデフォルト1."""
        from batch.kichiuma_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.kichiuma_scraper.scrape_races")
    def test_offset_days不正値はデフォルト1にフォールバック(self, mock_scrape_races):
        """正常系: offset_daysが不正値の場合はデフォルト1."""
        from batch.kichiuma_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 5}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.kichiuma_scraper.scrape_races")
    def test_offset_days文字列はデフォルト1にフォールバック(self, mock_scrape_races):
        """正常系: offset_daysが文字列の場合はデフォルト1."""
        from batch.kichiuma_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": "invalid"}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)
