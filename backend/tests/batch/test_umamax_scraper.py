"""うままっくす スクレイピングのテスト."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.umamax_scraper import (
    SOURCE_NAME,
    find_prediction_article_urls,
    parse_race_predictions_page,
    _parse_umamax_table,
    generate_race_id,
    save_predictions,
)
from batch.ai_shisu_scraper import VENUE_CODE_MAP

TEST_PARSER = "html.parser"


class TestSourceName:
    """SOURCE_NAME定数のテスト."""

    def test_SOURCE_NAMEが正しい(self):
        """正常系: SOURCE_NAMEが'umamax'."""
        assert SOURCE_NAME == "umamax"


class TestFindPredictionArticleUrls:
    """予想記事URL検索のテスト."""

    def test_対象日付の記事URLを取得(self):
        """正常系: 対象日付の記事URLリストを取得できる."""
        html = """
        <html><body>
            <a href="https://umamax.com/2026-02-08-kyoto-yosou-7r-12r/">京都7R-12R</a>
            <a href="https://umamax.com/2026-02-08-kyoto-yosou-1r-6r/">京都1R-6R</a>
            <a href="https://umamax.com/2026-02-08-tokyo-yosou-1r-6r/">東京1R-6R</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        articles = find_prediction_article_urls(soup, "20260208")

        assert len(articles) == 3
        assert articles[0]["venue"] == "京都"
        assert articles[0]["start_race"] == 7
        assert articles[0]["end_race"] == 12
        assert articles[1]["venue"] == "京都"
        assert articles[1]["start_race"] == 1
        assert articles[2]["venue"] == "東京"

    def test_別日の記事は除外(self):
        """正常系: 別日の記事はフィルタされる."""
        html = """
        <html><body>
            <a href="https://umamax.com/2026-02-07-kyoto-yosou-1r-6r/">京都前日</a>
            <a href="https://umamax.com/2026-02-08-kyoto-yosou-1r-6r/">京都当日</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        articles = find_prediction_article_urls(soup, "20260208")

        assert len(articles) == 1
        assert articles[0]["venue"] == "京都"

    def test_地方競馬のスラグは除外(self):
        """正常系: VENUE_SLUG_MAPにない競馬場は除外."""
        html = """
        <html><body>
            <a href="https://umamax.com/2026-02-08-ooi-yosou-1r-6r/">大井</a>
            <a href="https://umamax.com/2026-02-08-kyoto-yosou-1r-6r/">京都</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        articles = find_prediction_article_urls(soup, "20260208")

        assert len(articles) == 1
        assert articles[0]["venue"] == "京都"

    def test_記事がない場合は空リスト(self):
        """正常系: 記事がない場合は空リスト."""
        html = "<html><body><p>記事なし</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        articles = find_prediction_article_urls(soup, "20260208")

        assert articles == []

    def test_重複URLは除外(self):
        """正常系: 同じURLのリンクが複数あっても1つだけ返す."""
        html = """
        <html><body>
            <a href="https://umamax.com/2026-02-08-kyoto-yosou-1r-6r/">京都</a>
            <a href="https://umamax.com/2026-02-08-kyoto-yosou-1r-6r/">京都(重複)</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        articles = find_prediction_article_urls(soup, "20260208")

        assert len(articles) == 1


class TestParseUmamaxTable:
    """UM指数テーブルパースのテスト."""

    def test_正常なテーブルをパース(self):
        """正常系: UM指数テーブルからデータを抽出."""
        html = """
        <table>
            <tr><td>印</td><td>番</td><td>馬名</td><td>UM指数</td><td>差</td></tr>
            <tr><td>◎</td><td>5</td><td>テスト馬A</td><td>52.4</td><td>+3.2</td></tr>
            <tr><td>○</td><td>3</td><td>テスト馬B</td><td>49.2</td><td>0.0</td></tr>
            <tr><td>▲</td><td>8</td><td>テスト馬C</td><td>45.1</td><td>-4.1</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_umamax_table(table)

        assert len(predictions) == 3
        assert predictions[0]["rank"] == 1
        assert predictions[0]["score"] == 52.4
        assert predictions[0]["horse_number"] == 5
        assert predictions[0]["horse_name"] == "テスト馬A"
        assert predictions[1]["rank"] == 2
        assert predictions[1]["score"] == 49.2
        assert predictions[2]["rank"] == 3

    def test_スコア降順でランク再設定(self):
        """正常系: テーブル順序に関わらずスコア降順でランク付け."""
        html = """
        <table>
            <tr><td>-</td><td>1</td><td>馬C</td><td>30.0</td><td>0</td></tr>
            <tr><td>◎</td><td>2</td><td>馬A</td><td>55.0</td><td>0</td></tr>
            <tr><td>○</td><td>3</td><td>馬B</td><td>45.0</td><td>0</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_umamax_table(table)

        assert predictions[0]["horse_number"] == 2
        assert predictions[0]["rank"] == 1
        assert predictions[1]["horse_number"] == 3
        assert predictions[2]["horse_number"] == 1

    def test_数値変換失敗行はスキップ(self):
        """正常系: 馬番やUM指数の変換に失敗した行はスキップ."""
        html = """
        <table>
            <tr><td>◎</td><td>abc</td><td>馬A</td><td>52.4</td><td>0</td></tr>
            <tr><td>○</td><td>3</td><td>馬B</td><td>49.2</td><td>0</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_umamax_table(table)

        assert len(predictions) == 1
        assert predictions[0]["horse_name"] == "馬B"

    def test_空テーブル(self):
        """正常系: 空テーブルは空リスト."""
        html = "<table></table>"
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_umamax_table(table)

        assert predictions == []


class TestParseRacePredictionsPage:
    """記事ページパースのテスト."""

    def test_見出しありでレースを抽出(self):
        """正常系: h2/h3見出しからレース番号を取得しテーブルと対応付け."""
        html = """
        <html><body>
        <div class="entry-content">
            <h2>京都07R ４上 ダ1800</h2>
            <table>
                <tr><td>◎</td><td>5</td><td>馬A</td><td>52.4</td><td>0</td></tr>
            </table>
            <h2>京都08R ４上 芝2000</h2>
            <table>
                <tr><td>○</td><td>3</td><td>馬B</td><td>49.2</td><td>0</td></tr>
            </table>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_predictions_page(soup, "京都", 7)

        assert len(races) == 2
        assert races[0]["race_number"] == 7
        assert races[0]["venue"] == "京都"
        assert races[1]["race_number"] == 8

    def test_見出しなしでstart_raceから推定(self):
        """正常系: 見出しがない場合はstart_raceからレース番号を推定."""
        html = """
        <html><body>
        <article>
            <table>
                <tr><td>◎</td><td>5</td><td>馬A</td><td>52.4</td><td>0</td></tr>
            </table>
            <table>
                <tr><td>○</td><td>3</td><td>馬B</td><td>49.2</td><td>0</td></tr>
            </table>
        </article>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_predictions_page(soup, "東京", 7)

        assert len(races) == 2
        assert races[0]["race_number"] == 7
        assert races[1]["race_number"] == 8

    def test_空ページ(self):
        """正常系: テーブルがない場合は空リスト."""
        html = "<html><body><p>データなし</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_predictions_page(soup, "京都", 1)

        assert races == []


class TestGenerateRaceId:
    """race_id生成のテスト."""

    def test_正しい形式でrace_idを生成(self):
        """正常系: JRA-VANスタイルのrace_idを生成."""
        race_id = generate_race_id("20260208", "京都", 7)
        assert race_id == "20260208_08_07"

    def test_レース番号が1桁でもゼロパディング(self):
        """正常系: レース番号が1桁でも2桁にゼロパディング."""
        race_id = generate_race_id("20260208", "小倉", 1)
        assert race_id == "20260208_10_01"

    def test_すべての競馬場コード(self):
        """正常系: すべてのJRA競馬場でrace_idを生成."""
        for venue, code in VENUE_CODE_MAP.items():
            race_id = generate_race_id("20260208", venue, 12)
            assert race_id == f"20260208_{code}_12"


class TestSavePredictions:
    """DynamoDB保存のテスト."""

    def test_正常にDynamoDBに保存(self):
        """正常系: DynamoDBにデータを保存できる."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 6, 0, 0, tzinfo=JST)
        predictions = [
            {"rank": 1, "score": 52.4, "horse_number": 5, "horse_name": "馬A"},
        ]

        save_predictions(
            table=mock_table,
            race_id="20260208_08_07",
            venue="京都",
            race_number=7,
            predictions=predictions,
            scraped_at=scraped_at,
        )

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["race_id"] == "20260208_08_07"
        assert item["source"] == "umamax"
        assert item["venue"] == "京都"
        assert item["race_number"] == 7
        assert "ttl" in item
        expected_ttl = int((scraped_at + timedelta(days=7)).timestamp())
        assert item["ttl"] == expected_ttl

    def test_floatがDecimalに変換されてDynamoDBに保存される(self):
        """正常系: predictionsのfloat値がDecimalに変換されてDynamoDBに保存される."""
        from decimal import Decimal

        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 6, 0, 0, tzinfo=JST)
        predictions = [
            {"rank": 1, "score": 52.4, "horse_number": 5, "horse_name": "馬A"},
        ]

        save_predictions(
            table=mock_table,
            race_id="20260208_08_07",
            venue="京都",
            race_number=7,
            predictions=predictions,
            scraped_at=scraped_at,
        )

        item = mock_table.put_item.call_args.kwargs["Item"]
        saved_pred = item["predictions"][0]

        # float値がDecimalに変換されていること
        assert isinstance(saved_pred["score"], Decimal)
        assert saved_pred["score"] == Decimal("52.4")
        # int値はそのまま
        assert saved_pred["rank"] == 1
        assert saved_pred["horse_name"] == "馬A"


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch("batch.umamax_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.umamax_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    @patch("batch.umamax_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.umamax_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch top page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500

    @patch("batch.umamax_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.umamax_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert "error" in result["body"]

    @patch("batch.umamax_scraper.scrape_races")
    def test_offset_days_0を渡すと当日分を取得(self, mock_scrape_races):
        """正常系: offset_days=0 でscrape_racesに0を渡す."""
        from batch.umamax_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 0}, None)

        mock_scrape_races.assert_called_once_with(offset_days=0)

    @patch("batch.umamax_scraper.scrape_races")
    def test_offset_days_1を渡すと翌日分を取得(self, mock_scrape_races):
        """正常系: offset_days=1 でscrape_racesに1を渡す."""
        from batch.umamax_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 1}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.umamax_scraper.scrape_races")
    def test_offset_days省略時はデフォルト1(self, mock_scrape_races):
        """正常系: offset_daysが省略された場合はデフォルト1."""
        from batch.umamax_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.umamax_scraper.scrape_races")
    def test_offset_days不正値はデフォルト1にフォールバック(self, mock_scrape_races):
        """正常系: offset_daysが不正値の場合はデフォルト1."""
        from batch.umamax_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 5}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.umamax_scraper.scrape_races")
    def test_offset_days文字列はデフォルト1にフォールバック(self, mock_scrape_races):
        """正常系: offset_daysが文字列の場合はデフォルト1."""
        from batch.umamax_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": "invalid"}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)
