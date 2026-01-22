"""sync_jvlink.py のパーサーテスト."""
import pytest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestParseRaRecord:
    """RA レコード（レース情報）のパーステスト.

    JRA-VAN RA レコード構造（実際のデータ解析により特定）:
    - [0:2]     RecordType: "RA"
    - [11:19]   開催日: YYYYMMDD
    - [19:21]   場所コード
    - [21:23]   開催回
    - [23:25]   日目
    - [25:27]   レース番号
    - [507:509] トラックコード
    - [558:562] 距離（メートル）
    - [734:738] 発走時刻（HHMM）
    """

    def test_距離が正しくパースされる(self):
        """距離フィールドが位置558-562から正しく読み取られることを確認."""
        from sync_jvlink import parse_ra_record

        # 1133バイトのRAレコードを模擬
        data = "RA" + "0" * 9  # [0:11]
        data += "20260117"     # [11:19] 開催日
        data += "06"           # [19:21] 場所コード（中山）
        data += "01"           # [21:23] 開催回
        data += "06"           # [23:25] 日目
        data += "11"           # [25:27] レース番号
        data += "0" * 480      # [27:507] パディング
        data += "11"           # [507:509] トラックコード（芝・左）
        data += "0" * 49       # [509:558] パディング
        data += "1200"         # [558:562] 距離 1200m
        data += "0" * 172      # [562:734] パディング
        data += "1545"         # [734:738] 発走時刻
        data += "0" * 395      # [738:1133] パディング

        result = parse_ra_record(data)

        assert result is not None
        assert result["distance"] == 1200, f"距離が1200mであるべきだが、{result['distance']}mになっている"
        assert result["track_type"] == "芝"

    def test_カーバンクルステークスは1200m(self):
        """カーバンクルステークスの距離は1200mであるべき."""
        from sync_jvlink import parse_ra_record

        # カーバンクルステークス用のRA レコード（中山11R 芝1200m）
        data = "RA" + "0" * 9
        data += "20260117"     # 開催日
        data += "06"           # 中山
        data += "01"
        data += "06"
        data += "11"           # 11R
        data += "0" * 480
        data += "11"           # 芝
        data += "0" * 49
        data += "1200"         # 距離 1200m
        data += "0" * 172
        data += "1545"
        data += "0" * 395

        result = parse_ra_record(data)

        assert result is not None
        assert result["distance"] == 1200
        assert result["track_type"] == "芝"
        assert result["race_number"] == 11
        assert result["venue_code"] == "06"

    def test_短距離レースの距離が正しい(self):
        """短距離レース（1000m）も正しくパースされる."""
        from sync_jvlink import parse_ra_record

        data = "RA" + "0" * 9
        data += "20260117"
        data += "06"
        data += "01"
        data += "06"
        data += "01"           # 1R
        data += "0" * 480
        data += "22"           # ダート・右
        data += "0" * 49
        data += "1000"         # 距離 1000m
        data += "0" * 172
        data += "1005"
        data += "0" * 395

        result = parse_ra_record(data)

        assert result is not None
        assert result["distance"] == 1000
        assert result["track_type"] == "ダ"

    def test_長距離レースの距離が正しい(self):
        """長距離レース（3600m）も正しくパースされる."""
        from sync_jvlink import parse_ra_record

        data = "RA" + "0" * 9
        data += "20260117"
        data += "05"           # 東京
        data += "01"
        data += "06"
        data += "11"
        data += "0" * 480
        data += "12"           # 芝・右
        data += "0" * 49
        data += "3600"         # 距離 3600m
        data += "0" * 172
        data += "1540"
        data += "0" * 395

        result = parse_ra_record(data)

        assert result is not None
        assert result["distance"] == 3600
        assert result["track_type"] == "芝"

    def test_日経新春杯は2400m(self):
        """日経新春杯の距離は2400mであるべき（実データから確認）."""
        from sync_jvlink import parse_ra_record

        data = "RA" + "0" * 9
        data += "20260118"     # 1/18
        data += "08"           # 京都
        data += "01"
        data += "07"
        data += "11"
        data += "0" * 480
        data += "12"           # 芝
        data += "0" * 49
        data += "2400"         # 距離 2400m
        data += "0" * 172
        data += "1530"
        data += "0" * 395

        result = parse_ra_record(data)

        assert result is not None
        assert result["distance"] == 2400


class TestParseRaRecordRaceName:
    """RA レコードのレース名パーステスト.

    レース名は位置 32-92 に格納される（60バイト）。
    特別レース名が設定されている場合はそれを使用し、
    空の場合は「{場所名} {R}R」形式のデフォルト名を使用する。
    """

    def _build_ra_record_with_name(
        self,
        race_name: str,
        venue_code: str = "06",
        race_num: str = "11",
        distance: str = "1200",
    ) -> str:
        """指定したレース名を持つRAレコードを生成する."""
        data = "RA" + "0" * 9  # [0:11]
        data += "20260117"     # [11:19] 開催日
        data += venue_code     # [19:21] 場所コード
        data += "01"           # [21:23] 開催回
        data += "06"           # [23:25] 日目
        data += race_num       # [25:27] レース番号
        data += "0" * 5        # [27:32] パディング
        # レース名フィールド [32:92] - 60バイト
        name_field = race_name.ljust(60, "\u3000")[:60]  # 全角スペースでパディング
        data += name_field
        data += "0" * 415      # [92:507] パディング
        data += "11"           # [507:509] トラックコード
        data += "0" * 49       # [509:558] パディング
        data += distance       # [558:562] 距離
        data += "0" * 172      # [562:734] パディング
        data += "1545"         # [734:738] 発走時刻
        data += "0" * 395      # [738:1133] パディング
        return data

    def test_特別レース名が正しくパースされる(self):
        """特別レース名（カーバンクルステークス）が正しく取得される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_with_name("カーバンクルステークス")
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "カーバンクルステークス"

    def test_日経新春杯のレース名が正しくパースされる(self):
        """日経新春杯のレース名が正しく取得される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_with_name("日経新春杯", venue_code="08", distance="2400")
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "日経新春杯"

    def test_レース名が空の場合はデフォルト形式になる(self):
        """レース名フィールドが空の場合は「場所名 R」形式になる."""
        from sync_jvlink import parse_ra_record

        # 全角スペースのみのレース名
        data = self._build_ra_record_with_name("")
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "中山 11R"

    def test_全角スペースのみの場合はデフォルト形式になる(self):
        """レース名フィールドが全角スペースのみの場合もデフォルト形式になる."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_with_name("\u3000\u3000\u3000\u3000\u3000")
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "中山 11R"

    def test_東京競馬場のデフォルトレース名(self):
        """東京競馬場のデフォルトレース名が正しい."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_with_name("", venue_code="05", race_num="01")
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "東京 1R"

    def test_複数レース名の一貫性(self):
        """複数の特別レース名が正しくパースされる."""
        from sync_jvlink import parse_ra_record

        test_cases = [
            ("愛知杯", "07", "2000"),
            ("京成杯", "06", "2000"),
            ("フェアリーステークス", "06", "1600"),
        ]

        for race_name, venue_code, distance in test_cases:
            data = self._build_ra_record_with_name(
                race_name, venue_code=venue_code, distance=distance
            )
            result = parse_ra_record(data)

            assert result is not None, f"レース {race_name} のパースに失敗"
            assert result["race_name"] == race_name, (
                f"レース名が一致しない: expected={race_name}, "
                f"actual={result['race_name']}"
            )
