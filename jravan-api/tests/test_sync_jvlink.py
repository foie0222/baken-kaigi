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
