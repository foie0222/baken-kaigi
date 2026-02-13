"""JRAチェックサムスクレイパーのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

# テスト対象のモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))

from jra_checksum_scraper import (
    build_cname,
    build_access_url,
    is_valid_race_page,
    extract_checksums_from_nav,
    parse_cname,
    calculate_base_value,
    scrape_jra_checksums,
    _discover_venues_from_nav,
)


class TestBuildCname:
    """CNAME構築のテスト."""

    def test_東京1回1日目1R(self):
        """正常系: 東京1回1日目1RのCNAMEを構築."""
        cname = build_cname("05", "2026", "01", 1, 1, "20260207")
        # pw01dde + 0105 + 2026 + 01 + 01 + 01 + 20260207
        assert cname == "pw01dde0105202601010120260207"

    def test_京都2回3日目11R(self):
        """正常系: 京都2回3日目11RのCNAMEを構築."""
        cname = build_cname("08", "2026", "02", 3, 11, "20260208")
        # pw01dde + 0108 + 2026 + 02 + 03 + 11 + 20260208
        assert cname == "pw01dde0108202602031120260208"

    def test_小倉1回1日目1R(self):
        """正常系: 小倉1回1日目1RのCNAMEを構築."""
        cname = build_cname("10", "2026", "01", 1, 1, "20260207")
        # pw01dde + 0110 + 2026 + 01 + 01 + 01 + 20260207
        assert cname == "pw01dde0110202601010120260207"


class TestBuildAccessUrl:
    """アクセスURL構築のテスト."""

    def test_チェックサムを16進数で付加(self):
        """正常系: チェックサムが2桁16進数で付加される."""
        url = build_access_url("pw01dde0105202601010120260207", 0xAB)
        assert url == "https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0105202601010120260207/AB"

    def test_チェックサム0はゼロパディング(self):
        """正常系: チェックサム0は'00'."""
        url = build_access_url("test_cname", 0)
        assert url.endswith("/00")

    def test_チェックサム255はFF(self):
        """正常系: チェックサム255は'FF'."""
        url = build_access_url("test_cname", 255)
        assert url.endswith("/FF")


class TestIsValidRacePage:
    """ページ有効性判定のテスト."""

    def test_正常ページはTrue(self):
        """正常系: パラメータエラーを含まないページ."""
        html = "<html><head><title>出馬表</title></head><body>出走馬一覧</body></html>"
        assert is_valid_race_page(html) is True

    def test_パラメータエラーページはFalse(self):
        """正常系: パラメータエラーを含むページ."""
        html = "<html><head><title>パラメータエラー</title></head><body>不正なパラメータです</body></html>"
        assert is_valid_race_page(html) is False

    def test_空ページはTrue(self):
        """正常系: 空ページはエラーではないのでTrue."""
        assert is_valid_race_page("") is True


class TestExtractChecksumsFromNav:
    """ナビゲーションからのチェックサム抽出テスト."""

    def test_CNAMEリンクからチェックサムを抽出(self):
        """正常系: ナビゲーションのリンクからチェックサムを抽出."""
        html = """
        <html><body>
        <a href="accessD.html?CNAME=pw01dde0105202601010120260207/AB">東京1R</a>
        <a href="accessD.html?CNAME=pw01dde0108202602010120260207/CD">京都1R</a>
        </body></html>
        """
        result = extract_checksums_from_nav(html)

        assert result["pw01dde0105202601010120260207"] == 0xAB
        assert result["pw01dde0108202602010120260207"] == 0xCD

    def test_関連しないリンクは無視(self):
        """正常系: CNAME以外のリンクは無視される."""
        html = """
        <html><body>
        <a href="https://www.jra.go.jp/top/">JRAトップ</a>
        <a href="accessD.html?CNAME=pw01dde0105202601010120260207/AB">東京1R</a>
        </body></html>
        """
        result = extract_checksums_from_nav(html)

        assert len(result) == 1
        assert "pw01dde0105202601010120260207" in result

    def test_リンクがない場合は空辞書(self):
        """正常系: CNAMEリンクがない場合."""
        html = "<html><body><p>テスト</p></body></html>"
        result = extract_checksums_from_nav(html)
        assert result == {}

    def test_不正な形式のリンクは無視(self):
        """正常系: CNAME/HEX形式でないリンクは無視."""
        html = """
        <html><body>
        <a href="accessD.html?CNAME=pw01dde0105">不正形式</a>
        <a href="accessD.html?CNAME=pw01dde010520260101010120260207/ZZ">不正16進数</a>
        </body></html>
        """
        result = extract_checksums_from_nav(html)
        assert len(result) == 0


class TestParseCname:
    """CNAME解析のテスト."""

    def test_正常なCNAMEを解析(self):
        """正常系: CNAMEからレース情報を抽出."""
        result = parse_cname("pw01dde0105202601010120260207")

        assert result is not None
        assert result["venue_code"] == "05"
        assert result["year"] == "2026"
        assert result["kaisai_kai"] == "01"
        assert result["kaisai_nichime"] == 1
        assert result["race_number"] == 1
        assert result["date"] == "20260207"

    def test_京都2回3日目11R(self):
        """正常系: 京都2回3日目11R."""
        result = parse_cname("pw01dde0108202602031120260208")

        assert result is not None
        assert result["venue_code"] == "08"
        assert result["kaisai_kai"] == "02"
        assert result["kaisai_nichime"] == 3
        assert result["race_number"] == 11

    def test_不正なプレフィックス(self):
        """異常系: pw01ddeで始まらない."""
        result = parse_cname("invalid_cname")
        assert result is None

    def test_長さ不正(self):
        """異常系: 本体が22文字でない."""
        result = parse_cname("pw01dde01052026")
        assert result is None


class TestCalculateBaseValue:
    """base_value逆算のテスト."""

    def test_1日目は1Rチェックサムがそのままbase_value(self):
        """正常系: 日目=1のときbase_value = checksum_1r."""
        assert calculate_base_value(100, 1) == 100

    def test_2日目の逆算(self):
        """正常系: 日目=2のとき (checksum_1r - 48) % 256."""
        # base_value=100, nichime=2 → checksum_1r = (100 + 48) % 256 = 148
        assert calculate_base_value(148, 2) == 100

    def test_3日目の逆算(self):
        """正常系: 日目=3のとき (checksum_1r - 96) % 256."""
        # base_value=100, nichime=3 → checksum_1r = (100 + 96) % 256 = 196
        assert calculate_base_value(196, 3) == 100

    def test_オーバーフロー処理(self):
        """正常系: 256を超えた場合のmod処理."""
        # base_value=200, nichime=6 → checksum_1r = (200 + 240) % 256 = 184
        assert calculate_base_value(184, 6) == 200

    def test_calculateとの整合性(self):
        """正常系: database.calculate_jra_checksumと整合する."""
        base_value = 42
        nichime = 5
        # 順方向: 1Rチェックサムを計算
        checksum_1r = (base_value + (nichime - 1) * 48) % 256
        # 逆方向: base_valueを逆算
        assert calculate_base_value(checksum_1r, nichime) == base_value


class TestDiscoverVenuesFromNav:
    """ナビゲーションからの会場自動検出テスト."""

    def test_1Rリンクから会場を検出(self):
        """正常系: 1Rリンクから会場情報を抽出."""
        nav_checksums = {
            "pw01dde0105202601030120260207": 196,  # 東京1回3日目1R
            "pw01dde0105202601030220260207": 100,  # 東京1回3日目2R（無視）
            "pw01dde0108202602030120260207": 40,   # 京都2回3日目1R
        }

        result = _discover_venues_from_nav(nav_checksums, "20260207")

        assert len(result) == 2
        assert result[0]["venue_code"] == "05"
        assert result[0]["kaisai_kai"] == "01"
        assert result[0]["kaisai_nichime"] == 3
        assert result[1]["venue_code"] == "08"
        assert result[1]["kaisai_kai"] == "02"

    def test_異なる日付のリンクは除外(self):
        """正常系: target_dateと異なる日付のリンクは無視."""
        nav_checksums = {
            "pw01dde0105202601030120260207": 196,  # 2/7
            "pw01dde0108202602030120260208": 40,   # 2/8（異なる日付）
        }

        result = _discover_venues_from_nav(nav_checksums, "20260207")

        assert len(result) == 1
        assert result[0]["venue_code"] == "05"

    def test_空の場合は空リスト(self):
        """正常系: ナビゲーションが空の場合."""
        result = _discover_venues_from_nav({}, "20260207")
        assert result == []

    def test_不正なCNAMEは無視(self):
        """正常系: パースできないCNAMEは無視."""
        nav_checksums = {
            "invalid_cname": 100,
            "pw01dde0105202601030120260207": 196,
        }

        result = _discover_venues_from_nav(nav_checksums, "20260207")
        assert len(result) == 1


class TestScrapeJraChecksums:
    """メインスクレイピング関数のテスト."""

    @patch("jra_checksum_scraper.db")
    @patch("jra_checksum_scraper.find_valid_checksum")
    def test_DB情報なしかつブルートフォースも失敗時は空リスト(self, mock_find, mock_db):
        """異常系: DB開催情報なし・ブルートフォースでもページが見つからない."""
        mock_db.get_current_kaisai_info.return_value = []
        mock_find.return_value = None

        result = scrape_jra_checksums("20260207")

        assert result == []

    @patch("jra_checksum_scraper.db")
    @patch("jra_checksum_scraper.find_valid_checksum")
    @patch("jra_checksum_scraper.extract_checksums_from_nav")
    def test_全会場のbase_valueを保存(self, mock_extract, mock_find, mock_db):
        """正常系: 全会場のbase_valueを取得して保存する."""
        mock_db.get_current_kaisai_info.return_value = [
            {"venue_code": "05", "kaisai_kai": "01", "kaisai_nichime": 3, "date": "20260207"},
            {"venue_code": "08", "kaisai_kai": "02", "kaisai_nichime": 3, "date": "20260207"},
        ]

        mock_find.return_value = ("<html>valid page</html>", 0xAB)

        # ナビゲーションから取得されたチェックサム
        # 日目=3, base_value=100 → checksum_1r = (100 + 96) % 256 = 196
        # 日目=3, base_value=200 → checksum_1r = (200 + 96) % 256 = 40
        # CNAME: pw01dde + 01XX + 2026 + KK + NN + RR + YYYYMMDD
        mock_extract.return_value = {
            "pw01dde0105202601030120260207": 196,  # 東京1R: checksum=196 → base=100
            "pw01dde0108202602030120260207": 40,   # 京都1R: checksum=40 → base=200
        }

        mock_db.save_jra_checksum.return_value = True

        result = scrape_jra_checksums("20260207")

        assert len(result) == 2
        assert result[0]["venue_code"] == "05"
        assert result[0]["base_value"] == 100
        assert result[0]["status"] == "saved"
        assert result[1]["venue_code"] == "08"
        assert result[1]["base_value"] == 200
        assert result[1]["status"] == "saved"

        assert mock_db.save_jra_checksum.call_count == 2

    @patch("jra_checksum_scraper.db")
    @patch("jra_checksum_scraper.find_valid_checksum")
    def test_有効なチェックサムが見つからない場合(self, mock_find, mock_db):
        """異常系: DB情報あり・ブルートフォースで有効なページが見つからない."""
        mock_db.get_current_kaisai_info.return_value = [
            {"venue_code": "05", "kaisai_kai": "01", "kaisai_nichime": 1, "date": "20260207"},
        ]
        mock_find.return_value = None

        result = scrape_jra_checksums("20260207")

        assert result == []

    @patch("jra_checksum_scraper.db")
    @patch("jra_checksum_scraper.find_valid_checksum")
    @patch("jra_checksum_scraper.extract_checksums_from_nav")
    def test_一部会場のチェックサムが見つからない(self, mock_extract, mock_find, mock_db):
        """正常系: ナビから一部会場のチェックサムが取れない場合."""
        mock_db.get_current_kaisai_info.return_value = [
            {"venue_code": "05", "kaisai_kai": "01", "kaisai_nichime": 1, "date": "20260207"},
            {"venue_code": "08", "kaisai_kai": "02", "kaisai_nichime": 1, "date": "20260207"},
        ]

        mock_find.return_value = ("<html>valid</html>", 0x10)

        # 東京のみナビにある
        mock_extract.return_value = {
            "pw01dde0105202601010120260207": 100,
        }
        mock_db.save_jra_checksum.return_value = True

        result = scrape_jra_checksums("20260207")

        assert len(result) == 2
        assert result[0]["status"] == "saved"
        assert result[1]["status"] == "not_found"

    @patch("jra_checksum_scraper.db")
    @patch("jra_checksum_scraper.find_valid_checksum")
    @patch("jra_checksum_scraper.extract_checksums_from_nav")
    def test_DB保存エラー時もエラーステータスで返す(self, mock_extract, mock_find, mock_db):
        """異常系: DB保存に失敗してもエラーステータスで結果を返す."""
        mock_db.get_current_kaisai_info.return_value = [
            {"venue_code": "05", "kaisai_kai": "01", "kaisai_nichime": 1, "date": "20260207"},
        ]

        mock_find.return_value = ("<html>valid</html>", 0x10)
        mock_extract.return_value = {
            "pw01dde0105202601010120260207": 100,
        }
        mock_db.save_jra_checksum.side_effect = Exception("DB error")

        result = scrape_jra_checksums("20260207")

        assert len(result) == 1
        assert result[0]["base_value"] == 100
        assert "error" in result[0]["status"]

    @patch("jra_checksum_scraper.db")
    @patch("jra_checksum_scraper.find_valid_checksum")
    @patch("jra_checksum_scraper.extract_checksums_from_nav")
    def test_DB情報なしでもナビから会場を検出して保存(self, mock_extract, mock_find, mock_db):
        """正常系: DB開催情報なしでもナビゲーションから会場を自動検出."""
        mock_db.get_current_kaisai_info.return_value = []

        # ブルートフォースで東京05/01/nichime=3 で見つかる想定
        mock_find.return_value = ("<html>valid page</html>", 0xAB)

        mock_extract.return_value = {
            "pw01dde0105202601030120260207": 196,  # 東京1R
            "pw01dde0105202601030220260207": 100,  # 東京2R（1R以外は無視）
            "pw01dde0108202602030120260207": 40,   # 京都1R
        }

        mock_db.save_jra_checksum.return_value = True

        result = scrape_jra_checksums("20260207")

        assert len(result) == 2
        assert result[0]["venue_code"] == "05"
        assert result[0]["base_value"] == 100
        assert result[0]["status"] == "saved"
        assert result[1]["venue_code"] == "08"
        assert result[1]["base_value"] == 200
        assert result[1]["status"] == "saved"
