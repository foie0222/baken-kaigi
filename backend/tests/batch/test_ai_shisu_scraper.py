"""AI指数スクレイピングのテスト."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from bs4 import BeautifulSoup

# テスト対象のモジュールをインポート
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.ai_shisu_scraper import (
    find_today_event_date_url,
    parse_venue_list,
    parse_race_list,
    parse_race_predictions,
    generate_race_id,
    save_predictions,
    VENUE_CODE_MAP,
)

# テスト用パーサー（lxmlはLambda環境でのみ利用可能）
TEST_PARSER = "html.parser"


class TestFindTodayEventDateUrl:
    """開催日URLを探すテスト."""

    def test_今日の日付リンクを取得(self):
        """正常系: 今日の日付ページURLを取得できる."""
        html = """
        <html>
        <body>
            <ul>
                <li><a href="/event_dates/2494">1/30(金)</a></li>
                <li><a href="/event_dates/2495">1/31(土)</a></li>
                <li><a href="/event_dates/2496">2/1(日)</a></li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_today_event_date_url(soup, "1/31")

        assert url == "/event_dates/2495"

    def test_日付が見つからない場合(self):
        """正常系: 該当日付がない場合はNone."""
        html = """
        <html>
        <body>
            <ul>
                <li><a href="/event_dates/2494">1/30(金)</a></li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        url = find_today_event_date_url(soup, "1/31")

        assert url is None


class TestParseVenueList:
    """競馬場リストのパースのテスト."""

    def test_JRA競馬場を抽出(self):
        """正常系: JRA中央競馬場のリンクを抽出できる."""
        html = """
        <html>
        <body>
            <ul>
                <li><a href="/event_places/9887">東京</a></li>
                <li><a href="/event_places/9888">京都</a></li>
                <li><a href="/event_places/9889">小倉</a></li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        venues = parse_venue_list(soup)

        assert len(venues) == 3
        assert venues[0] == {"url": "/event_places/9887", "venue": "東京"}
        assert venues[1] == {"url": "/event_places/9888", "venue": "京都"}
        assert venues[2] == {"url": "/event_places/9889", "venue": "小倉"}

    def test_地方競馬場は除外(self):
        """正常系: 地方競馬場は除外される."""
        html = """
        <html>
        <body>
            <ul>
                <li><a href="/event_places/9887">東京</a></li>
                <li><a href="/event_places/9890">佐賀</a></li>
                <li><a href="/event_places/9891">大井</a></li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        venues = parse_venue_list(soup)

        assert len(venues) == 1
        assert venues[0]["venue"] == "東京"


class TestParseRaceList:
    """競馬場ページからのレース一覧パースのテスト."""

    def test_レース一覧を抽出(self):
        """正常系: 競馬場ページからレースリンクを抽出できる."""
        html = """
        <html>
        <body>
            <ul>
                <li><a href="/races/114761">1R 10:05</a></li>
                <li><a href="/races/114762">2R 10:35</a></li>
                <li><a href="/races/114771">11R 15:45</a></li>
                <li><a href="/races/114772">12R 16:25</a></li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list(soup, "東京")

        assert len(races) == 4
        assert races[0] == {"url": "/races/114761", "venue": "東京", "race_number": 1}
        assert races[1] == {"url": "/races/114762", "venue": "東京", "race_number": 2}
        assert races[2] == {"url": "/races/114771", "venue": "東京", "race_number": 11}
        assert races[3] == {"url": "/races/114772", "venue": "東京", "race_number": 12}

    def test_レースがない場合(self):
        """正常系: レースがない場合は空リスト."""
        html = "<html><body><p>レースはありません</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list(soup, "東京")

        assert races == []


class TestParseRacePredictions:
    """AI指数データのパースのテスト."""

    def test_AI指数テーブルをパース(self):
        """正常系: AI指数データをテーブルから抽出できる."""
        html = """
        <html>
        <body>
            <table>
                <tr><th>指数</th><th>順位</th></tr>
                <tr>
                    <td>1位</td>
                    <td>691点</td>
                    <td>8番</td>
                    <td>ピースワンデュック</td>
                </tr>
                <tr>
                    <td>2位</td>
                    <td>650点</td>
                    <td>3番</td>
                    <td>テスト馬</td>
                </tr>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert len(predictions) == 2
        assert predictions[0] == {
            "rank": 1, "score": 691, "horse_number": 8, "horse_name": "ピースワンデュック"
        }
        assert predictions[1] == {
            "rank": 2, "score": 650, "horse_number": 3, "horse_name": "テスト馬"
        }

    def test_順位でソートされる(self):
        """正常系: 結果は順位でソートされる."""
        html = """
        <html>
        <body>
            <table>
                <tr><td>3位</td><td>500点</td><td>1番</td><td>馬C</td></tr>
                <tr><td>1位</td><td>700点</td><td>2番</td><td>馬A</td></tr>
                <tr><td>2位</td><td>600点</td><td>3番</td><td>馬B</td></tr>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert predictions[0]["rank"] == 1
        assert predictions[1]["rank"] == 2
        assert predictions[2]["rank"] == 3

    def test_データがない場合(self):
        """正常系: AI指数データがない場合は空リスト."""
        html = "<html><body><p>データなし</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert predictions == []


class TestGenerateRaceId:
    """race_id生成のテスト."""

    def test_正しい形式でrace_idを生成(self):
        """正常系: JRA-VANスタイルのrace_idを生成."""
        race_id = generate_race_id("20260131", "東京", 11)
        assert race_id == "20260131_05_11"

    def test_レース番号が1桁でもゼロパディング(self):
        """正常系: レース番号が1桁でも2桁にゼロパディング."""
        race_id = generate_race_id("20260131", "小倉", 1)
        assert race_id == "20260131_10_01"

    def test_すべての競馬場コード(self):
        """正常系: すべてのJRA競馬場でrace_idを生成."""
        for venue, code in VENUE_CODE_MAP.items():
            race_id = generate_race_id("20260131", venue, 12)
            assert race_id == f"20260131_{code}_12"


class TestSavePredictions:
    """DynamoDB保存のテスト."""

    def test_正常にDynamoDBに保存(self):
        """正常系: DynamoDBにデータを保存できる."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 1, 31, 6, 0, 0, tzinfo=JST)
        predictions = [
            {"rank": 1, "score": 691, "horse_number": 8, "horse_name": "馬A"},
        ]

        save_predictions(
            table=mock_table,
            race_id="20260131_05_11",
            venue="東京",
            race_number=11,
            predictions=predictions,
            scraped_at=scraped_at,
        )

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["race_id"] == "20260131_05_11"
        assert item["source"] == "ai-shisu"
        assert item["venue"] == "東京"
        assert item["race_number"] == 11
        assert item["predictions"] == predictions
        assert "ttl" in item
        # TTLは7日後
        expected_ttl = int((scraped_at + timedelta(days=7)).timestamp())
        assert item["ttl"] == expected_ttl


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch("batch.ai_shisu_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.ai_shisu_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True
        assert result["body"]["races_scraped"] == 5

    @patch("batch.ai_shisu_scraper.scrape_races")
    def test_部分失敗時はsuccess_trueだがerrorsあり(self, mock_scrape_races):
        """正常系: 一部失敗してもレースが取得できればsuccess=True."""
        from batch.ai_shisu_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 3,
            "errors": ["Failed to fetch 京都 12R"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True
        assert len(result["body"]["errors"]) == 1

    @patch("batch.ai_shisu_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.ai_shisu_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch race list page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False

    @patch("batch.ai_shisu_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.ai_shisu_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False
        assert "error" in result["body"]
