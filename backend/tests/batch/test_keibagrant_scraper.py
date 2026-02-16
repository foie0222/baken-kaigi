"""競馬グラント馬柱スクレイピングのテスト."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.keibagrant_scraper import (
    SOURCE_NAME,
    find_article_url,
    parse_race_pdf_links,
    _parse_weight,
    _find_sire_line,
    _find_dam_sire_line,
    generate_race_id,
    save_race_data,
)
from batch.ai_shisu_scraper import VENUE_CODE_MAP


class TestSourceName:
    """SOURCE_NAME定数のテスト."""

    def test_SOURCE_NAMEが正しい(self):
        """正常系: SOURCE_NAMEが'keibagrant'."""
        assert SOURCE_NAME == "keibagrant"


class TestFindArticleUrl:
    """記事URL検索のテスト."""

    def test_対象日付の記事URLを取得(self):
        """正常系: 対象日付の記事URLを取得できる."""
        html = '''
        <a href="https://keibagrant.jp/?p=16205" class="entry-card-wrap" title="2月7日（土） 1回東京3日 出馬表"></a>
        <a href="https://keibagrant.jp/?p=16206" class="entry-card-wrap" title="2月8日（日） 1回東京4日 出馬表"></a>
        '''
        url = find_article_url(html, "2月8日")

        assert url == "https://keibagrant.jp/?p=16206"

    def test_記事が見つからない場合はNone(self):
        """正常系: 対象日付の記事がない場合はNone."""
        html = '''
        <a href="https://keibagrant.jp/?p=16205" class="entry-card-wrap" title="2月7日（土） 1回東京3日 出馬表"></a>
        '''
        url = find_article_url(html, "2月8日")

        assert url is None

    def test_回数情報がないリンクは除外(self):
        """正常系: N回の情報がないリンクはマッチしない."""
        html = '''
        <a href="https://keibagrant.jp/?p=16206" class="entry-card-wrap" title="2月8日（日） お知らせ"></a>
        '''
        url = find_article_url(html, "2月8日")

        assert url is None


class TestParseRacePdfLinks:
    """レースPDFリンク抽出のテスト."""

    def test_PDFリンクを抽出(self):
        """正常系: 競馬場名とレースPDFリンクを抽出."""
        html = '''
        <p><a href="http://example.com/all.pdf">1回東京4日</a></p>
        <li><a href="http://example.com/1r.pdf">1R</a></li>
        <li><a href="http://example.com/11r.pdf">11R</a></li>
        '''
        races = parse_race_pdf_links(html)

        assert len(races) == 2
        assert races[0]["venue"] == "東京"
        assert races[0]["race_number"] == 1
        assert races[0]["pdf_url"] == "http://example.com/1r.pdf"
        assert races[1]["race_number"] == 11

    def test_複数競馬場(self):
        """正常系: 複数の競馬場のPDFリンクを抽出."""
        html = '''
        <p><a href="http://example.com/tokyo.pdf">1回東京4日</a></p>
        <li><a href="http://example.com/t1r.pdf">1R</a></li>
        <p><a href="http://example.com/kyoto.pdf">1回京都4日</a></p>
        <li><a href="http://example.com/k1r.pdf">1R</a></li>
        '''
        races = parse_race_pdf_links(html)

        assert len(races) == 2
        assert races[0]["venue"] == "東京"
        assert races[1]["venue"] == "京都"

    def test_PDFリンクがない場合は空リスト(self):
        """正常系: PDFリンクがない場合は空リスト."""
        html = "<p>データなし</p>"
        races = parse_race_pdf_links(html)

        assert races == []


class TestParseWeight:
    """斤量パースのテスト."""

    def test_2桁の斤量(self):
        """正常系: 2桁の斤量はそのままfloatに."""
        assert _parse_weight("58") == 58.0
        assert _parse_weight("55") == 55.0

    def test_3桁の斤量は小数点付き(self):
        """正常系: 3桁は末尾1桁が小数."""
        assert _parse_weight("585") == 58.5
        assert _parse_weight("575") == 57.5
        assert _parse_weight("555") == 55.5


class TestFindSireLine:
    """父行検索のテスト."""

    def test_父行を検出(self):
        """正常系: 性年齢パターンを含む行を検出."""
        # prev_horse_line_idx=0 の場合 search_start = max(0+4, 0) = 4
        # horse_line_idx=10 で、search_start=4 以上のインデックスで検索
        lines = [
            "",
            "",
            "",
            "",
            "",  # index 4
            "",
            "                テスト種牡馬    牡4  25.11.23 98",  # index 6
            "                騎手名",
            "                母馬名",
            "     1  5  テスト馬",  # index 9
        ]
        result = _find_sire_line(lines, 9, 0)

        assert result == 6

    def test_父行が見つからない場合はNone(self):
        """正常系: 該当行がない場合はNone."""
        lines = [
            "                テスト情報",
            "     1  5  テスト馬",
        ]
        result = _find_sire_line(lines, 1, 0)

        assert result is None


class TestFindDamSireLine:
    """母父行検索のテスト."""

    def test_母父行を検出(self):
        """正常系: (母父名) パターンと距離情報を含む行を検出."""
        lines = [
            "     1  5  テスト馬",
            "                (テスト母父)   1600m  芝C 良 1:32.6",
        ]
        result = _find_dam_sire_line(lines, 0)

        assert result == 1

    def test_母父行が見つからない場合はNone(self):
        """正常系: 該当行がない場合はNone."""
        lines = [
            "     1  5  テスト馬",
            "                その他情報",
        ]
        result = _find_dam_sire_line(lines, 0)

        assert result is None


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


class TestSaveRaceData:
    """DynamoDB保存のテスト."""

    def test_正常にDynamoDBに保存(self):
        """正常系: DynamoDBに馬柱データを保存できる."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 6, 0, 0, tzinfo=JST)
        horses = [
            {
                "horse_number": 1,
                "horse_name": "テスト馬",
                "sire": "父馬",
                "dam": "母馬",
                "dam_sire": "母父馬",
                "past_races": [],
            },
        ]

        save_race_data(
            table=mock_table,
            race_id="202602080511",
            venue="東京",
            race_number=11,
            horses=horses,
            scraped_at=scraped_at,
        )

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["race_id"] == "202602080511"
        assert item["source"] == "keibagrant"
        assert item["venue"] == "東京"
        assert item["race_number"] == 11
        assert item["horses"] == horses
        assert "ttl" in item
        expected_ttl = int((scraped_at + timedelta(days=7)).timestamp())
        assert item["ttl"] == expected_ttl

    def test_scraped_atがISO形式で保存(self):
        """正常系: scraped_atがISO形式で保存される."""
        mock_table = MagicMock()
        JST = timezone(timedelta(hours=9))
        scraped_at = datetime(2026, 2, 8, 21, 0, 0, tzinfo=JST)
        horses = [{"horse_number": 1, "horse_name": "馬", "sire": "", "dam": "", "dam_sire": "", "past_races": []}]

        save_race_data(
            table=mock_table,
            race_id="202602080511",
            venue="東京",
            race_number=11,
            horses=horses,
            scraped_at=scraped_at,
        )

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["scraped_at"] == scraped_at.isoformat()


class TestHandler:
    """Lambdaハンドラーのテスト."""

    @patch("batch.keibagrant_scraper.scrape_races")
    def test_正常終了時は200を返す(self, mock_scrape_races):
        """正常系: スクレイピング成功時はstatusCode 200."""
        from batch.keibagrant_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 24,
            "errors": [],
        }

        result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    @patch("batch.keibagrant_scraper.scrape_races")
    def test_全失敗時は500を返す(self, mock_scrape_races):
        """異常系: 全て失敗した場合はstatusCode 500."""
        from batch.keibagrant_scraper import handler

        mock_scrape_races.return_value = {
            "success": False,
            "races_scraped": 0,
            "errors": ["Failed to fetch category page"],
        }

        result = handler({}, None)

        assert result["statusCode"] == 500

    @patch("batch.keibagrant_scraper.scrape_races")
    def test_例外発生時は500を返す(self, mock_scrape_races):
        """異常系: 例外発生時はstatusCode 500."""
        from batch.keibagrant_scraper import handler

        mock_scrape_races.side_effect = Exception("Unexpected error")

        result = handler({}, None)

        assert result["statusCode"] == 500
        assert "error" in result["body"]

    @patch("batch.keibagrant_scraper.scrape_races")
    def test_offset_days_0を渡すと当日分を取得(self, mock_scrape_races):
        """正常系: offset_days=0 でscrape_racesに0を渡す."""
        from batch.keibagrant_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 0}, None)

        mock_scrape_races.assert_called_once_with(offset_days=0)

    @patch("batch.keibagrant_scraper.scrape_races")
    def test_offset_days_1を渡すと翌日分を取得(self, mock_scrape_races):
        """正常系: offset_days=1 でscrape_racesに1を渡す."""
        from batch.keibagrant_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 1}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.keibagrant_scraper.scrape_races")
    def test_offset_days省略時はデフォルト1(self, mock_scrape_races):
        """正常系: offset_daysが省略された場合はデフォルト1."""
        from batch.keibagrant_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.keibagrant_scraper.scrape_races")
    def test_offset_days不正値はデフォルト1にフォールバック(self, mock_scrape_races):
        """正常系: offset_daysが不正値の場合はデフォルト1."""
        from batch.keibagrant_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": 5}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)

    @patch("batch.keibagrant_scraper.scrape_races")
    def test_offset_days文字列はデフォルト1にフォールバック(self, mock_scrape_races):
        """正常系: offset_daysが文字列の場合はデフォルト1."""
        from batch.keibagrant_scraper import handler

        mock_scrape_races.return_value = {
            "success": True,
            "races_scraped": 12,
            "errors": [],
        }

        handler({"offset_days": "invalid"}, None)

        mock_scrape_races.assert_called_once_with(offset_days=1)
