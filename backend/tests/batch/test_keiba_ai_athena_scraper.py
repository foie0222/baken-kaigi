"""競馬AI ATHENA スクレイピングのテスト."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.keiba_ai_athena_scraper import (
    SOURCE_NAME,
    find_prediction_article_url,
    parse_race_predictions_page,
    _parse_athena_table,
    generate_race_id,
    save_predictions,
)
from batch.ai_shisu_scraper import VENUE_CODE_MAP

TEST_PARSER = "html.parser"


class TestSourceName:
    """SOURCE_NAME定数のテスト."""

    def test_SOURCE_NAMEが正しい(self):
        """正常系: SOURCE_NAMEが'keiba-ai-athena'."""
        assert SOURCE_NAME == "keiba-ai-athena"


class TestFindPredictionArticleUrl:
    """予想記事URL取得のテスト."""

    def test_対象日付の予想記事URLを取得(self):
        """正常系: 対象日付のAI予想記事URLを取得できる."""
        html = """
        <html><body>
            <a href="https://keiba-ai.jp/archives/2968">2026年02月07日(土)のレース結果</a>
            <a href="https://keiba-ai.jp/archives/2969">2026年02月08日(日)のレースAI予想【きさらぎ賞】</a>
            <a href="https://keiba-ai.jp/archives/2970">2026年02月08日(日)のレース結果</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_prediction_article_url(soup, "20260208")

        assert url == "https://keiba-ai.jp/archives/2969"

    def test_結果記事は除外(self):
        """正常系: 「結果」を含む記事は除外される."""
        html = """
        <html><body>
            <a href="https://keiba-ai.jp/archives/2970">2026年02月08日(日)のレース結果</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_prediction_article_url(soup, "20260208")

        assert url is None

    def test_記事が見つからない場合(self):
        """正常系: 対象日付の記事がない場合はNone."""
        html = """
        <html><body>
            <a href="https://keiba-ai.jp/archives/2965">2026年02月01日(土)のレースAI予想</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_prediction_article_url(soup, "20260208")

        assert url is None

    def test_AI予想を含まない記事は除外(self):
        """正常系: AI予想を含まないリンクは除外."""
        html = """
        <html><body>
            <a href="https://keiba-ai.jp/archives/2969">2026年02月08日(日)のレースお知らせ</a>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_prediction_article_url(soup, "20260208")

        assert url is None


class TestParseAthenaTable:
    """ATHENAテーブルパースのテスト."""

    def test_正常なテーブルをパース(self):
        """正常系: ATHENAのテーブルから予想データを抽出."""
        html = """
        <table>
            <tr><td>14</td><td>プレデンシア</td><td>牝3/56</td><td>坂井瑠</td><td>3.5</td><td>1</td><td>17.113 %(755)</td><td>1</td><td></td></tr>
            <tr><td>8</td><td>テスト馬<span>(父名)</span></td><td>牡3/56</td><td>戸崎圭</td><td>5.0</td><td>2</td><td>12.5 %(650)</td><td>2</td><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_athena_table(table)

        assert len(predictions) == 2
        assert predictions[0]["rank"] == 1
        assert predictions[0]["score"] == 755
        assert predictions[0]["horse_number"] == 14
        assert predictions[1]["rank"] == 2
        assert predictions[1]["score"] == 650
        assert predictions[1]["horse_number"] == 8

    def test_スコア降順でランク再設定(self):
        """正常系: スコア降順でランクが再設定される."""
        html = """
        <table>
            <tr><td>1</td><td>馬A</td><td>牡3</td><td>騎手A</td><td>10.0</td><td>3</td><td>5.0 %(500)</td><td>3</td><td></td></tr>
            <tr><td>2</td><td>馬B</td><td>牡3</td><td>騎手B</td><td>5.0</td><td>1</td><td>15.0 %(700)</td><td>1</td><td></td></tr>
            <tr><td>3</td><td>馬C</td><td>牡3</td><td>騎手C</td><td>8.0</td><td>2</td><td>10.0 %(600)</td><td>2</td><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_athena_table(table)

        assert predictions[0]["horse_number"] == 2
        assert predictions[0]["score"] == 700
        assert predictions[0]["rank"] == 1
        assert predictions[1]["horse_number"] == 3
        assert predictions[1]["rank"] == 2
        assert predictions[2]["horse_number"] == 1
        assert predictions[2]["rank"] == 3

    def test_AI指数の括弧がない行はスキップ(self):
        """正常系: AI指数に括弧がない行はスキップされる."""
        html = """
        <table>
            <tr><td>1</td><td>馬A</td><td>牡3</td><td>騎手A</td><td>10.0</td><td>3</td><td>5.0 %</td><td>3</td><td></td></tr>
            <tr><td>2</td><td>馬B</td><td>牡3</td><td>騎手B</td><td>5.0</td><td>1</td><td>15.0 %(700)</td><td>1</td><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_athena_table(table)

        assert len(predictions) == 1
        assert predictions[0]["horse_number"] == 2

    def test_セル数が足りない行はスキップ(self):
        """正常系: 7セル未満の行はスキップ."""
        html = """
        <table>
            <tr><th>番</th><th>馬名</th></tr>
            <tr><td>2</td><td>馬B</td><td>牡3</td><td>騎手B</td><td>5.0</td><td>1</td><td>15.0 %(700)</td><td>1</td><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_athena_table(table)

        assert len(predictions) == 1

    def test_空テーブル(self):
        """正常系: データがないテーブルは空リスト."""
        html = "<table><tr><th>番</th><th>馬名</th></tr></table>"
        soup = BeautifulSoup(html, TEST_PARSER)
        table = soup.find("table")
        predictions = _parse_athena_table(table)

        assert predictions == []


class TestParseRacePredictionsPage:
    """記事ページ全体のパースのテスト."""

    def test_複数競馬場のレースを抽出(self):
        """正常系: 複数競馬場のレース予想を抽出できる."""
        html = """
        <html><body>
        <div class="entry-body">
            <h2>京都</h2>
            <div class="su-box-title">01R</div>
            <table>
                <tr><td>1</td><td>馬A</td><td>牡3</td><td>騎手</td><td>5.0</td><td>1</td><td>10.0 %(700)</td><td>1</td><td></td></tr>
            </table>
            <h2>東京</h2>
            <div class="su-box-title">11R</div>
            <table>
                <tr><td>5</td><td>馬B</td><td>牡3</td><td>騎手</td><td>3.0</td><td>1</td><td>15.0 %(800)</td><td>1</td><td></td></tr>
            </table>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_predictions_page(soup)

        assert len(races) == 2
        assert races[0]["venue"] == "京都"
        assert races[0]["race_number"] == 1
        assert len(races[0]["predictions"]) == 1
        assert races[1]["venue"] == "東京"
        assert races[1]["race_number"] == 11

    def test_地方競馬場は除外(self):
        """正常系: JRA以外の競馬場はスキップ."""
        html = """
        <html><body>
        <div class="entry-body">
            <h2>大井</h2>
            <div class="su-box-title">01R</div>
            <table>
                <tr><td>1</td><td>馬A</td><td>牡3</td><td>騎手</td><td>5.0</td><td>1</td><td>10.0 %(700)</td><td>1</td><td></td></tr>
            </table>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_predictions_page(soup)

        assert races == []

    def test_entry_bodyがない場合もパース可能(self):
        """正常系: entry-bodyがない場合はarticleタグから探す."""
        html = """
        <html><body>
        <article>
            <h2>東京</h2>
            <div class="su-box-title">01R</div>
            <table>
                <tr><td>1</td><td>馬A</td><td>牡3</td><td>騎手</td><td>5.0</td><td>1</td><td>10.0 %(700)</td><td>1</td><td></td></tr>
            </table>
        </article>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_predictions_page(soup)

        assert len(races) == 1


class TestGenerateRaceId:
    """race_id生成のテスト."""

    def test_正しい形式でrace_idを生成(self):
        """正常系: JRA-VANスタイルのrace_idを生成."""
        race_id = generate_race_id("20260208", "京都", 11)
        assert race_id == "202602080811"

    def test_レース番号が1桁でもゼロパディング(self):
        """正常系: レース番号が1桁でも2桁にゼロパディング."""
        race_id = generate_race_id("20260208", "小倉", 1)
        assert race_id == "202602081001"

    def test_すべての競馬場コード(self):
        """正常系: すべてのJRA競馬場でrace_idを生成."""
        for venue, code in VENUE_CODE_MAP.items():
            race_id = generate_race_id("20260208", venue, 12)
            assert race_id == f"20260208{code}12"


class TestSavePredictions:
    """DynamoDB保存のテスト."""

    def test_正常にDynamoDBに保存(self):
        """正常系: DynamoDBにデータを保存できる."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 6, 0, 0, tzinfo=JST)
        predictions = [
            {"rank": 1, "score": 755, "horse_number": 14, "horse_name": "馬A"},
        ]

        save_predictions(
            table=mock_table,
            race_id="202602080811",
            venue="京都",
            race_number=11,
            predictions=predictions,
            scraped_at=scraped_at,
        )

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["race_id"] == "202602080811"
        assert item["source"] == "keiba-ai-athena"
        assert item["venue"] == "京都"
        assert item["race_number"] == 11
        assert item["predictions"] == predictions
        assert "ttl" in item
        expected_ttl = int((scraped_at + timedelta(days=7)).timestamp())
        assert item["ttl"] == expected_ttl

    def test_scraped_atがISO形式で保存(self):
        """正常系: scraped_atがISO形式で保存される."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 21, 0, 0, tzinfo=JST)
        predictions = [{"rank": 1, "score": 755, "horse_number": 14, "horse_name": "馬A"}]

        save_predictions(
            table=mock_table,
            race_id="202602080811",
            venue="京都",
            race_number=11,
            predictions=predictions,
            scraped_at=scraped_at,
        )

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["scraped_at"] == scraped_at.isoformat()


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch("batch.keiba_ai_athena_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.keiba_ai_athena_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True
        assert result["body"]["races_scraped"] == 5

    @patch("batch.keiba_ai_athena_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.keiba_ai_athena_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch top page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False

    @patch("batch.keiba_ai_athena_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.keiba_ai_athena_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False
        assert "error" in result["body"]
