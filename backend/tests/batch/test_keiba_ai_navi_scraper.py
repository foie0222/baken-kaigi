"""競馬AIナビ スクレイピングのテスト."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.keiba_ai_navi_scraper import (
    SOURCE_NAME,
    extract_race_data_json,
    parse_race_predictions,
    generate_race_id,
    save_predictions,
    _extract_json_from_position,
)
from batch.ai_shisu_scraper import VENUE_CODE_MAP

TEST_PARSER = "html.parser"


class TestSourceName:
    """SOURCE_NAME定数のテスト."""

    def test_SOURCE_NAMEが正しい(self):
        """正常系: SOURCE_NAMEが'keiba-ai-navi'."""
        assert SOURCE_NAME == "keiba-ai-navi"


class TestExtractRaceDataJson:
    """レースデータJSON抽出のテスト."""

    def test_dual_index_report_dataからJSON抽出(self):
        """正常系: id=dual-index-report-dataからJSONを抽出できる."""
        html = """
        <html><body>
            <script id="dual-index-report-data">
                {"20260208": [{"keibajo_code": "05", "keibajo_name": "東京", "race_bango": 1, "horses": []}]}
            </script>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        result = extract_race_data_json(soup, "20260208")

        assert result is not None
        assert len(result) == 1
        assert result[0]["keibajo_name"] == "東京"

    def test_対象日付がない場合はNone(self):
        """正常系: 対象日付のデータがない場合はNone."""
        html = """
        <html><body>
            <script id="dual-index-report-data">
                {"20260207": [{"keibajo_code": "05", "keibajo_name": "東京", "race_bango": 1, "horses": []}]}
            </script>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        result = extract_race_data_json(soup, "20260208")

        assert result is None

    def test_JSONが不正な場合はNone(self):
        """異常系: JSONパースに失敗した場合はNone."""
        html = """
        <html><body>
            <script id="dual-index-report-data">
                {invalid json}
            </script>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        result = extract_race_data_json(soup, "20260208")

        assert result is None

    def test_scriptタグ内のJSONから抽出(self):
        """正常系: scriptタグ内のJSONからフォールバック抽出できる."""
        # フォールバック検索にはscript内に "keibajo_code" と 日付文字列が必要
        # また {"20260208":[ で始まるJSONが必要
        json_data = '{"20260208":[{"keibajo_code":"08","keibajo_name":"京都","race_bango":1,"horses":[]}]}'
        html = f"""
        <html><body>
            <script>
                var data = {json_data};
            </script>
        </body></html>
        """
        soup = BeautifulSoup(html, TEST_PARSER)
        result = extract_race_data_json(soup, "20260208")

        assert result is not None
        assert result[0]["keibajo_name"] == "京都"

    def test_データがまったくない場合(self):
        """正常系: データがない場合はNone."""
        html = "<html><body><p>データなし</p></body></html>"
        soup = BeautifulSoup(html, TEST_PARSER)
        result = extract_race_data_json(soup, "20260208")

        assert result is None


class TestExtractJsonFromPosition:
    """JSON抽出ヘルパーのテスト."""

    def test_正常なJSON抽出(self):
        """正常系: JSON部分を正しく切り出せる."""
        text = 'var x = {"key": [1, 2, 3]}; console.log(x);'
        result = _extract_json_from_position(text, 8)

        assert result == {"key": [1, 2, 3]}

    def test_ネストされたJSON(self):
        """正常系: ネストされたJSONも正しく抽出."""
        text = '{"a": {"b": {"c": 1}}}'
        result = _extract_json_from_position(text, 0)

        assert result == {"a": {"b": {"c": 1}}}

    def test_文字列内のブレースは無視(self):
        """正常系: 文字列内の波括弧は無視される."""
        text = '{"key": "value with { and }"}'
        result = _extract_json_from_position(text, 0)

        assert result == {"key": "value with { and }"}


class TestParseRacePredictions:
    """レース予想データパースのテスト."""

    def test_正常なレースデータをパース(self):
        """正常系: horsesからAI予想を抽出."""
        race_data = {
            "keibajo_code": "05",
            "keibajo_name": "東京",
            "race_bango": 1,
            "horses": [
                {"umaban": 1, "umamei": "馬A", "tansho_index": 17.1, "fukusho_index": 30.5, "kitaichi_index": -10},
                {"umaban": 5, "umamei": "馬B", "tansho_index": 8.5, "fukusho_index": 20.2, "kitaichi_index": -25},
                {"umaban": 3, "umamei": "馬C", "tansho_index": 12.3, "fukusho_index": 25.0, "kitaichi_index": -15},
            ],
        }

        predictions = parse_race_predictions(race_data)

        assert len(predictions) == 3
        assert predictions[0]["rank"] == 1
        assert predictions[0]["score"] == 17.1
        assert predictions[0]["horse_number"] == 1
        assert predictions[0]["horse_name"] == "馬A"
        assert predictions[0]["fukusho_index"] == 30.5
        assert predictions[0]["kitaichi_index"] == -10
        assert predictions[1]["rank"] == 2
        assert predictions[1]["score"] == 12.3
        assert predictions[2]["rank"] == 3
        assert predictions[2]["score"] == 8.5

    def test_馬番が範囲外の馬は除外(self):
        """正常系: 馬番が1-18以外の馬は除外される."""
        race_data = {
            "horses": [
                {"umaban": 0, "umamei": "馬A", "tansho_index": 17.1, "fukusho_index": 0, "kitaichi_index": 0},
                {"umaban": 19, "umamei": "馬B", "tansho_index": 8.5, "fukusho_index": 0, "kitaichi_index": 0},
                {"umaban": 5, "umamei": "馬C", "tansho_index": 12.3, "fukusho_index": 0, "kitaichi_index": 0},
            ],
        }

        predictions = parse_race_predictions(race_data)

        assert len(predictions) == 1
        assert predictions[0]["horse_number"] == 5

    def test_データが不完全な馬はスキップ(self):
        """正常系: umaban/umamei/tansho_indexがない馬はスキップ."""
        race_data = {
            "horses": [
                {"umaban": 1, "umamei": "", "tansho_index": 17.1, "fukusho_index": 0, "kitaichi_index": 0},
                {"umaban": None, "umamei": "馬B", "tansho_index": 8.5, "fukusho_index": 0, "kitaichi_index": 0},
                {"umaban": 5, "umamei": "馬C", "tansho_index": None, "fukusho_index": 0, "kitaichi_index": 0},
                {"umaban": 3, "umamei": "馬D", "tansho_index": 10.0, "fukusho_index": 0, "kitaichi_index": 0},
            ],
        }

        predictions = parse_race_predictions(race_data)

        assert len(predictions) == 1
        assert predictions[0]["horse_name"] == "馬D"

    def test_horsesが空の場合(self):
        """正常系: horsesが空の場合は空リスト."""
        race_data = {"horses": []}
        predictions = parse_race_predictions(race_data)

        assert predictions == []

    def test_horsesキーがない場合(self):
        """正常系: horsesキーがない場合は空リスト."""
        race_data = {}
        predictions = parse_race_predictions(race_data)

        assert predictions == []


class TestGenerateRaceId:
    """race_id生成のテスト."""

    def test_正しい形式でrace_idを生成(self):
        """正常系: JRA-VANスタイルのrace_idを生成."""
        race_id = generate_race_id("20260208", "東京", 11)
        assert race_id == "20260208_05_11"

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
            {"rank": 1, "score": 17.1, "horse_number": 1, "horse_name": "馬A"},
        ]

        save_predictions(
            table=mock_table,
            race_id="20260208_05_11",
            venue="東京",
            race_number=11,
            predictions=predictions,
            scraped_at=scraped_at,
        )

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["race_id"] == "20260208_05_11"
        assert item["source"] == "keiba-ai-navi"
        assert item["venue"] == "東京"
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
        predictions = [{"rank": 1, "score": 17.1, "horse_number": 1, "horse_name": "馬A"}]

        save_predictions(
            table=mock_table,
            race_id="20260208_05_11",
            venue="東京",
            race_number=11,
            predictions=predictions,
            scraped_at=scraped_at,
        )

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["scraped_at"] == scraped_at.isoformat()


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch("batch.keiba_ai_navi_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.keiba_ai_navi_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 5,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    @patch("batch.keiba_ai_navi_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.keiba_ai_navi_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch prediction page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False

    @patch("batch.keiba_ai_navi_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.keiba_ai_navi_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False
        assert "error" in result["body"]
