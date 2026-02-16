"""無料競馬AI スクレイピングのテスト."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

# テスト対象のモジュールをインポート
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.muryou_keiba_ai_scraper import (
    SOURCE_NAME,
    parse_race_list_page,
    parse_race_predictions,
    extract_race_info,
    generate_race_id,
    save_predictions,
)
from batch.ai_shisu_scraper import VENUE_CODE_MAP

# テスト用パーサー（lxmlはLambda環境でのみ利用可能）
TEST_PARSER = "html.parser"


class TestSourceName:
    """SOURCE_NAME定数のテスト."""

    def test_SOURCE_NAMEが正しい(self):
        """正常系: SOURCE_NAMEが'muryou-keiba-ai'."""
        assert SOURCE_NAME == "muryou-keiba-ai"


class TestParseRaceListPage:
    """アーカイブページからのレース一覧パースのテスト."""

    def test_レース一覧を抽出(self):
        """正常系: アーカイブページからレースリンクを抽出できる."""
        html = """
        <html>
        <body>
            <ul>
                <li>
                    <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19477/">
                        京都 2月8日 1R 09:55
                        3歳未勝利 ダート 1200m 16頭
                    </a>
                </li>
                <li>
                    <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19487/">
                        京都 2月8日 11R 15:30
                        きさらぎ賞 芝 1800m 9頭
                    </a>
                </li>
                <li>
                    <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19501/">
                        東京 2月8日 5R 12:15
                        3歳未勝利 芝 1600m 14頭
                    </a>
                </li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list_page(soup, "20260208")

        assert len(races) == 3
        assert races[0]["url"] == "https://muryou-keiba-ai.jp/predict/2026/02/05/19477/"
        assert races[0]["venue"] == "京都"
        assert races[0]["race_number"] == 1
        assert races[0]["date_str"] == "20260208"

        assert races[1]["venue"] == "京都"
        assert races[1]["race_number"] == 11

        assert races[2]["venue"] == "東京"
        assert races[2]["race_number"] == 5

    def test_対象日付以外のレースは除外(self):
        """正常系: 対象日付以外のレースはフィルタされる."""
        html = """
        <html>
        <body>
            <ul>
                <li>
                    <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19477/">
                        京都 2月8日 1R 09:55
                        3歳未勝利 ダート 1200m 16頭
                    </a>
                </li>
                <li>
                    <a href="https://muryou-keiba-ai.jp/predict/2026/02/07/19400/">
                        東京 2月7日 1R 09:55
                        3歳未勝利 ダート 1200m 16頭
                    </a>
                </li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list_page(soup, "20260208")

        assert len(races) == 1
        assert races[0]["venue"] == "京都"

    def test_地方競馬場は除外(self):
        """正常系: JRA中央競馬場以外は除外される."""
        html = """
        <html>
        <body>
            <ul>
                <li>
                    <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19477/">
                        京都 2月8日 1R 09:55
                        3歳未勝利 ダート 1200m 16頭
                    </a>
                </li>
                <li>
                    <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19500/">
                        佐賀 2月8日 1R 10:00
                        C1 ダート 1300m 12頭
                    </a>
                </li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list_page(soup, "20260208")

        assert len(races) == 1
        assert races[0]["venue"] == "京都"

    def test_レースがない場合は空リスト(self):
        """正常系: レースがない場合は空リスト."""
        html = "<html><body><p>レースはありません</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list_page(soup, "20260208")

        assert races == []

    def test_URLが不正なリンクは除外(self):
        """正常系: predict形式でないリンクは無視."""
        html = """
        <html>
        <body>
            <ul>
                <li><a href="/about/">サイトについて</a></li>
                <li>
                    <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19477/">
                        京都 2月8日 1R 09:55
                        3歳未勝利 ダート 1200m 16頭
                    </a>
                </li>
            </ul>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        races = parse_race_list_page(soup, "20260208")

        assert len(races) == 1


class TestExtractRaceInfo:
    """リンクテキストからレース情報を抽出するテスト."""

    def test_通常のレース情報を抽出(self):
        """正常系: 競馬場名とレース番号を抽出できる."""
        text = "京都 2月8日 1R 09:55 3歳未勝利 ダート 1200m 16頭"
        info = extract_race_info(text)

        assert info["venue"] == "京都"
        assert info["race_number"] == 1

    def test_二桁レース番号(self):
        """正常系: 11R等の二桁レース番号を抽出できる."""
        text = "東京 2月8日 11R 15:30 きさらぎ賞 芝 1800m 9頭"
        info = extract_race_info(text)

        assert info["venue"] == "東京"
        assert info["race_number"] == 11

    def test_全競馬場名を認識(self):
        """正常系: 全JRA競馬場名を認識する."""
        for venue in VENUE_CODE_MAP:
            text = f"{venue} 2月8日 1R 09:55 3歳未勝利"
            info = extract_race_info(text)
            assert info["venue"] == venue

    def test_地方競馬場はNone(self):
        """正常系: 地方競馬場はNoneを返す."""
        text = "佐賀 2月8日 1R 10:00 C1 ダート 1300m 12頭"
        info = extract_race_info(text)

        assert info is None

    def test_レース番号なしはNone(self):
        """正常系: レース番号が取れない場合はNone."""
        text = "京都 2月8日 特別レース"
        info = extract_race_info(text)

        assert info is None


class TestParseRacePredictions:
    """AI予想データのパースのテスト."""

    def test_実際のHTML構造からAI予想を抽出(self):
        """正常系: 実際のサイト構造（クラスがp要素、スコアがspan）から抽出."""
        html = """
        <html>
        <body>
            <table class="race_table baken_race_table">
                <thead>
                    <tr>
                        <th class="umaban_head">馬番</th>
                        <th class="bamei_head">馬名・騎手名</th>
                        <th class="ninki_head">人気</th>
                        <th class="predict_head"><strong>AI予想</strong></th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><p class="umaban_wrap waku_2">2</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei bamei_link"><strong>エムズビギン</strong></a><span class="kisyu">川田将雅</span></p></td>
                        <td><p class="ninki_wrap"><span class="ninki">1</span></p></td>
                        <td><p class="predict_wrap predict_1"><span class="mark">◎</span><span class="predict">65.7</span></p></td>
                    </tr>
                    <tr>
                        <td><p class="umaban_wrap waku_1">1</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei bamei_link"><strong>ゾロアストロ</strong></a><span class="kisyu">騎手不明</span></p></td>
                        <td><p class="ninki_wrap"><span class="ninki">2</span></p></td>
                        <td><p class="predict_wrap predict_2"><span class="mark">○</span><span class="predict">65.6</span></p></td>
                    </tr>
                    <tr>
                        <td><p class="umaban_wrap waku_7">7</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei bamei_link"><strong>ラフターラインズ</strong></a><span class="kisyu">藤岡佑介</span></p></td>
                        <td><p class="ninki_wrap"><span class="ninki">3</span></p></td>
                        <td><p class="predict_wrap predict_3"><span class="mark">▲</span><span class="predict">55.9</span></p></td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert len(predictions) == 3
        # スコア降順でランク付けされる
        assert predictions[0] == {
            "rank": 1,
            "score": 65.7,
            "horse_number": 2,
            "horse_name": "エムズビギン",
        }
        assert predictions[1] == {
            "rank": 2,
            "score": 65.6,
            "horse_number": 1,
            "horse_name": "ゾロアストロ",
        }
        assert predictions[2] == {
            "rank": 3,
            "score": 55.9,
            "horse_number": 7,
            "horse_name": "ラフターラインズ",
        }

    def test_印なしの馬も含む(self):
        """正常系: 印が付いていない馬（スコアのみ）も抽出できる."""
        html = """
        <html>
        <body>
            <table class="race_table baken_race_table">
                <tbody>
                    <tr>
                        <td><p class="umaban_wrap">2</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬A</strong></a></p></td>
                        <td><p class="predict_wrap predict_1"><span class="mark">◎</span><span class="predict">65.7</span></p></td>
                    </tr>
                    <tr>
                        <td><p class="umaban_wrap">5</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬B</strong></a></p></td>
                        <td><p class="predict_wrap"><span class="predict">40.2</span></p></td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert len(predictions) == 2
        assert predictions[0]["score"] == 65.7
        assert predictions[0]["horse_name"] == "馬A"
        assert predictions[1]["score"] == 40.2
        assert predictions[1]["horse_name"] == "馬B"

    def test_スコア降順でランク付け(self):
        """正常系: スコア降順で順位が付けられる."""
        html = """
        <html>
        <body>
            <table class="race_table baken_race_table">
                <tbody>
                    <tr>
                        <td><p class="umaban_wrap">3</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬C</strong></a></p></td>
                        <td><p class="predict_wrap"><span class="predict">50.0</span></p></td>
                    </tr>
                    <tr>
                        <td><p class="umaban_wrap">1</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬A</strong></a></p></td>
                        <td><p class="predict_wrap"><span class="mark">◎</span><span class="predict">70.0</span></p></td>
                    </tr>
                    <tr>
                        <td><p class="umaban_wrap">2</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬B</strong></a></p></td>
                        <td><p class="predict_wrap"><span class="mark">○</span><span class="predict">60.0</span></p></td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert predictions[0]["rank"] == 1
        assert predictions[0]["horse_number"] == 1
        assert predictions[0]["score"] == 70.0

        assert predictions[1]["rank"] == 2
        assert predictions[1]["horse_number"] == 2
        assert predictions[1]["score"] == 60.0

        assert predictions[2]["rank"] == 3
        assert predictions[2]["horse_number"] == 3
        assert predictions[2]["score"] == 50.0

    def test_データがない場合は空リスト(self):
        """正常系: AI予想データがない場合は空リスト."""
        html = "<html><body><p>データなし</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert predictions == []

    def test_race_tableがない場合は空リスト(self):
        """正常系: race_tableクラスがない場合は空リスト."""
        html = """
        <html>
        <body>
            <table>
                <tr><td>1</td><td>テスト</td></tr>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert predictions == []

    def test_馬番が数値でない行はスキップ(self):
        """正常系: 馬番が数値変換できない行はスキップ."""
        html = """
        <html>
        <body>
            <table class="race_table baken_race_table">
                <thead>
                    <tr>
                        <th class="umaban_head">馬番</th>
                        <th class="bamei_head">馬名</th>
                        <th class="predict_head">AI予想</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><p class="umaban_wrap">2</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬A</strong></a></p></td>
                        <td><p class="predict_wrap"><span class="mark">◎</span><span class="predict">65.7</span></p></td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert len(predictions) == 1
        assert predictions[0]["horse_name"] == "馬A"

    def test_小数点なしのスコア(self):
        """正常系: 小数点なしのスコア（整数）も処理できる."""
        html = """
        <html>
        <body>
            <table class="race_table baken_race_table">
                <tbody>
                    <tr>
                        <td><p class="umaban_wrap">1</p></td>
                        <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬A</strong></a></p></td>
                        <td><p class="predict_wrap"><span class="predict">70</span></p></td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        predictions = parse_race_predictions(soup)

        assert len(predictions) == 1
        assert predictions[0]["score"] == 70.0


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
            {"rank": 1, "score": 65.7, "horse_number": 2, "horse_name": "馬A"},
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
        assert item["source"] == "muryou-keiba-ai"
        assert item["venue"] == "京都"
        assert item["race_number"] == 11
        # float→Decimal変換されていることを確認
        assert item["predictions"] == [
            {"rank": 1, "score": Decimal("65.7"), "horse_number": 2, "horse_name": "馬A"},
        ]
        assert "ttl" in item
        # TTLは7日後
        expected_ttl = int((scraped_at + timedelta(days=7)).timestamp())
        assert item["ttl"] == expected_ttl

    def test_scraped_atがISO形式で保存(self):
        """正常系: scraped_atがISO形式で保存される."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 21, 0, 0, tzinfo=JST)
        predictions = [{"rank": 1, "score": 65.7, "horse_number": 2, "horse_name": "馬A"}]

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

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True
        assert result["body"]["races_scraped"] == 5

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_部分失敗時はsuccess_trueだがerrorsあり(self, mock_scrape_races):
        """正常系: 一部失敗してもレースが取得できればsuccess=True."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 3,
            "errors": ["Failed to fetch 京都 12R"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True
        assert len(result["body"]["errors"]) == 1

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch archive page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False
        assert "error" in result["body"]

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_offset_daysをイベントから渡す(self, mock_scrape_races):
        """正常系: eventのoffset_daysをscrape_racesに渡す."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        handler({"offset_days": 0}, None)

        mock_scrape_races.assert_called_once_with(offset_days=0)

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_offset_days未指定時はデフォルト1(self, mock_scrape_races):
        """正常系: offset_days未指定時はデフォルト値1（翌日）."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        handler({}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_offset_daysが文字列の場合はint変換(self, mock_scrape_races):
        """正常系: offset_daysが文字列でもint変換される."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        handler({"offset_days": "0"}, None)

        mock_scrape_races.assert_called_once_with(offset_days=0)

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_offset_daysが不正値の場合はデフォルト1(self, mock_scrape_races):
        """異常系: offset_daysが不正な値の場合はデフォルト1にフォールバック."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        handler({"offset_days": "abc"}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.muryou_keiba_ai_scraper.scrape_races")
    def test_offset_daysが範囲外の場合はデフォルト1(self, mock_scrape_races):
        """異常系: offset_daysが0,1以外の場合はデフォルト1にフォールバック."""
        from batch.muryou_keiba_ai_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        handler({"offset_days": 5}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)


class TestScrapeRaces:
    """メインスクレイピング処理のテスト."""

    @patch("batch.muryou_keiba_ai_scraper.datetime")
    @patch("batch.muryou_keiba_ai_scraper.save_predictions")
    @patch("batch.muryou_keiba_ai_scraper.fetch_page")
    @patch("batch.muryou_keiba_ai_scraper.get_dynamodb_table")
    def test_正常なスクレイピングフロー(self, mock_get_table, mock_fetch, mock_save, mock_dt):
        """正常系: アーカイブ→レースページ→保存の全フロー."""
        from batch.muryou_keiba_ai_scraper import scrape_races

        # 2026/2/7 21:00 JST に固定 → 翌日は 2/8
        JST = timezone(timedelta(hours=9))
        fixed_now = datetime(2026, 2, 7, 21, 0, 0, tzinfo=JST)
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = datetime

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        # アーカイブページのHTML
        archive_html = """
        <html><body><ul>
            <li>
                <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19477/">
                    京都 2月8日 1R 09:55
                    3歳未勝利 ダート 1200m 16頭
                </a>
            </li>
        </ul></body></html>
        """
        # レースページのHTML（実際のサイト構造）
        race_html = """
        <html><body>
            <table class="race_table baken_race_table"><tbody>
                <tr>
                    <td><p class="umaban_wrap">2</p></td>
                    <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬A</strong></a></p></td>
                    <td><p class="predict_wrap"><span class="mark">◎</span><span class="predict">65.7</span></p></td>
                </tr>
                <tr>
                    <td><p class="umaban_wrap">1</p></td>
                    <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬B</strong></a></p></td>
                    <td><p class="predict_wrap"><span class="mark">○</span><span class="predict">55.3</span></p></td>
                </tr>
            </tbody></table>
        </body></html>
        """

        archive_soup = BeautifulSoup(archive_html, TEST_PARSER)
        race_soup = BeautifulSoup(race_html, TEST_PARSER)
        mock_fetch.side_effect = [archive_soup, race_soup]

        results = scrape_races()

        assert results["success"] is True
        assert results["races_scraped"] == 1
        assert results["errors"] == []
        mock_save.assert_called_once()

    @patch("batch.muryou_keiba_ai_scraper.fetch_page")
    @patch("batch.muryou_keiba_ai_scraper.get_dynamodb_table")
    def test_アーカイブページ取得失敗(self, mock_get_table, mock_fetch):
        """異常系: アーカイブページの取得に失敗した場合."""
        from batch.muryou_keiba_ai_scraper import scrape_races

        mock_get_table.return_value = MagicMock()
        mock_fetch.return_value = None

        results = scrape_races()

        assert results["success"] is False
        assert results["races_scraped"] == 0
        assert len(results["errors"]) > 0

    @patch("batch.muryou_keiba_ai_scraper.datetime")
    @patch("batch.muryou_keiba_ai_scraper.fetch_page")
    @patch("batch.muryou_keiba_ai_scraper.get_dynamodb_table")
    def test_レースページ取得失敗(self, mock_get_table, mock_fetch, mock_dt):
        """異常系: レースページの取得に失敗した場合."""
        from batch.muryou_keiba_ai_scraper import scrape_races

        # 2026/2/7 21:00 JST に固定 → 翌日は 2/8
        JST = timezone(timedelta(hours=9))
        fixed_now = datetime(2026, 2, 7, 21, 0, 0, tzinfo=JST)
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = datetime

        mock_get_table.return_value = MagicMock()

        archive_html = """
        <html><body><ul>
            <li>
                <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19477/">
                    京都 2月8日 1R 09:55
                    3歳未勝利 ダート 1200m 16頭
                </a>
            </li>
        </ul></body></html>
        """
        archive_soup = BeautifulSoup(archive_html, TEST_PARSER)
        mock_fetch.side_effect = [archive_soup, None]

        results = scrape_races()

        assert results["races_scraped"] == 0
        assert len(results["errors"]) > 0

    @patch("batch.muryou_keiba_ai_scraper.datetime")
    @patch("batch.muryou_keiba_ai_scraper.save_predictions")
    @patch("batch.muryou_keiba_ai_scraper.fetch_page")
    @patch("batch.muryou_keiba_ai_scraper.get_dynamodb_table")
    def test_offset_days_0で当日分を取得(self, mock_get_table, mock_fetch, mock_save, mock_dt):
        """正常系: offset_days=0 の場合、当日のレースを取得する."""
        from batch.muryou_keiba_ai_scraper import scrape_races

        # 2026/2/8 09:30 JST（レース当日朝）
        JST = timezone(timedelta(hours=9))
        fixed_now = datetime(2026, 2, 8, 9, 30, 0, tzinfo=JST)
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = datetime

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        archive_html = """
        <html><body><ul>
            <li>
                <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19477/">
                    京都 2月8日 1R 09:55
                    3歳未勝利 ダート 1200m 16頭
                </a>
            </li>
        </ul></body></html>
        """
        race_html = """
        <html><body>
            <table class="race_table baken_race_table"><tbody>
                <tr>
                    <td><p class="umaban_wrap">1</p></td>
                    <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬A</strong></a></p></td>
                    <td><p class="predict_wrap"><span class="mark">◎</span><span class="predict">70.0</span></p></td>
                </tr>
            </tbody></table>
        </body></html>
        """

        archive_soup = BeautifulSoup(archive_html, TEST_PARSER)
        race_soup = BeautifulSoup(race_html, TEST_PARSER)
        mock_fetch.side_effect = [archive_soup, race_soup]

        results = scrape_races(offset_days=0)

        assert results["success"] is True
        assert results["races_scraped"] == 1
        # 当日 2/8 のアーカイブページにアクセスしていること
        fetch_url = mock_fetch.call_args_list[0][0][0]
        assert "y=2026" in fetch_url
        assert "month=02" in fetch_url
        # race_id は 当日 20260208
        save_call = mock_save.call_args
        assert save_call.kwargs["race_id"] == "202602080801"

    @patch("batch.muryou_keiba_ai_scraper.datetime")
    @patch("batch.muryou_keiba_ai_scraper.save_predictions")
    @patch("batch.muryou_keiba_ai_scraper.fetch_page")
    @patch("batch.muryou_keiba_ai_scraper.get_dynamodb_table")
    def test_offset_days_1で翌日分を取得(self, mock_get_table, mock_fetch, mock_save, mock_dt):
        """正常系: offset_days=1 の場合、翌日のレースを取得する（従来動作）."""
        from batch.muryou_keiba_ai_scraper import scrape_races

        # 2026/2/7 21:00 JST（前日夜）
        JST = timezone(timedelta(hours=9))
        fixed_now = datetime(2026, 2, 7, 21, 0, 0, tzinfo=JST)
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = datetime

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        archive_html = """
        <html><body><ul>
            <li>
                <a href="https://muryou-keiba-ai.jp/predict/2026/02/05/19477/">
                    京都 2月8日 1R 09:55
                    3歳未勝利 ダート 1200m 16頭
                </a>
            </li>
        </ul></body></html>
        """
        race_html = """
        <html><body>
            <table class="race_table baken_race_table"><tbody>
                <tr>
                    <td><p class="umaban_wrap">1</p></td>
                    <td><p class="bamei_wrap"><a href="#" class="bamei"><strong>馬A</strong></a></p></td>
                    <td><p class="predict_wrap"><span class="mark">◎</span><span class="predict">70.0</span></p></td>
                </tr>
            </tbody></table>
        </body></html>
        """

        archive_soup = BeautifulSoup(archive_html, TEST_PARSER)
        race_soup = BeautifulSoup(race_html, TEST_PARSER)
        mock_fetch.side_effect = [archive_soup, race_soup]

        results = scrape_races(offset_days=1)

        assert results["success"] is True
        assert results["races_scraped"] == 1
        save_call = mock_save.call_args
        assert save_call.kwargs["race_id"] == "202602080801"
