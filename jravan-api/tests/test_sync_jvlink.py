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
        syubetu_cd: str = "12",  # 種別コード（馬齢条件）: 12=3歳
        jyoken_cd: str = "999",  # 条件コード（クラス）: 999=オープン
    ) -> str:
        """指定したレース名を持つRAレコードを生成する.

        Args:
            race_name: 本題（特別レース名）。空の場合は条件コードから生成
            venue_code: 場所コード
            race_num: レース番号
            distance: 距離（メートル）
            syubetu_cd: 種別コード（馬齢条件）11=2歳, 12=3歳, 13=3歳以上, 14=4歳以上
            jyoken_cd: 条件コード 701=新馬, 703=未勝利, 704=1勝, 705=2勝, 706=3勝, 999=オープン
        """
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
        data += syubetu_cd     # [507:509] 種別コード（馬齢条件）
        data += "0" * 7        # [509:516] パディング
        data += jyoken_cd      # [516:519] 条件コード（クラス）
        data += "0" * 39       # [519:558] パディング
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

    def test_レース名が空で条件コードがある場合は条件名が使われる(self):
        """本題が空で条件コードがある場合は条件名が生成される."""
        from sync_jvlink import parse_ra_record

        # 本題なし、条件コードあり（デフォルト: 3歳オープン）
        data = self._build_ra_record_with_name("")
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "3歳オープン"

    def test_全角スペースのみの場合も条件名が使われる(self):
        """本題が全角スペースのみの場合も条件名が生成される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_with_name("\u3000\u3000\u3000\u3000\u3000")
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "3歳オープン"

    def test_条件コードがない場合はデフォルト形式になる(self):
        """条件コードが無効な場合は「場所名 R」形式になる."""
        from sync_jvlink import parse_ra_record

        # 条件コードを無効な値に設定
        data = self._build_ra_record_with_name(
            "", venue_code="05", race_num="01",
            syubetu_cd="00",  # 無効
            jyoken_cd="000",  # 無効
        )
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


class TestParseRaRecordConditionName:
    """一般条件戦（未勝利、1勝クラス等）のレース名パーステスト.

    本題（特別レース名）が空の場合、SyubetuCd（種別コード）と
    JyokenCd（条件コード）から「3歳未勝利」等のレース名を生成する。

    フィールド位置:
    - [507:509] SyubetuCd: 種別コード（馬齢条件）
    - [516:519] JyokenCd: 条件コード（クラス）
    """

    def _build_ra_record_for_condition(
        self,
        venue_code: str = "06",
        race_num: str = "01",
        distance: str = "1200",
        syubetu_cd: str = "12",
        jyoken_cd: str = "703",
    ) -> str:
        """条件戦用のRAレコードを生成する（本題は空）."""
        data = "RA" + "0" * 9  # [0:11]
        data += "20260118"     # [11:19] 開催日
        data += venue_code     # [19:21] 場所コード
        data += "01"           # [21:23] 開催回
        data += "07"           # [23:25] 日目
        data += race_num       # [25:27] レース番号
        data += "0" * 5        # [27:32] パディング
        # レース名フィールド [32:92] - 60バイト（全角スペースで埋める）
        data += "\u3000" * 60
        data += "0" * 415      # [92:507] パディング
        data += syubetu_cd     # [507:509] 種別コード（馬齢条件）
        data += "0" * 7        # [509:516] パディング
        data += jyoken_cd      # [516:519] 条件コード（クラス）
        data += "0" * 39       # [519:558] パディング
        data += distance       # [558:562] 距離
        data += "0" * 172      # [562:734] パディング
        data += "1005"         # [734:738] 発走時刻
        data += "0" * 395      # [738:1133] パディング
        return data

    def test_3歳未勝利が正しく生成される(self):
        """SyubetuCd=12, JyokenCd=703 で「3歳未勝利」が生成される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_for_condition(
            syubetu_cd="12",  # 3歳
            jyoken_cd="703",  # 未勝利
        )
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "3歳未勝利"

    def test_3歳新馬が正しく生成される(self):
        """SyubetuCd=12, JyokenCd=701 で「3歳新馬」が生成される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_for_condition(
            syubetu_cd="12",  # 3歳
            jyoken_cd="701",  # 新馬
        )
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "3歳新馬"

    def test_2歳未勝利が正しく生成される(self):
        """SyubetuCd=11, JyokenCd=703 で「2歳未勝利」が生成される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_for_condition(
            syubetu_cd="11",  # 2歳
            jyoken_cd="703",  # 未勝利
        )
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "2歳未勝利"

    def test_4歳以上1勝クラスが正しく生成される(self):
        """SyubetuCd=14, JyokenCd=704 で「4歳以上1勝クラス」が生成される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_for_condition(
            syubetu_cd="14",  # 4歳以上
            jyoken_cd="704",  # 1勝クラス
        )
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "4歳以上1勝クラス"

    def test_3歳以上2勝クラスが正しく生成される(self):
        """SyubetuCd=13, JyokenCd=705 で「3歳以上2勝クラス」が生成される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_for_condition(
            syubetu_cd="13",  # 3歳以上
            jyoken_cd="705",  # 2勝クラス
        )
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "3歳以上2勝クラス"

    def test_3歳以上3勝クラスが正しく生成される(self):
        """SyubetuCd=13, JyokenCd=706 で「3歳以上3勝クラス」が生成される."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_for_condition(
            syubetu_cd="13",  # 3歳以上
            jyoken_cd="706",  # 3勝クラス
        )
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "3歳以上3勝クラス"

    def test_オープンクラスは種別名のみ表示しない(self):
        """JyokenCd=999（オープン）の場合は「オープン」のみになる."""
        from sync_jvlink import parse_ra_record

        data = self._build_ra_record_for_condition(
            syubetu_cd="13",  # 3歳以上
            jyoken_cd="999",  # オープン
        )
        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "3歳以上オープン"

    def test_本題がある場合は条件名より優先される(self):
        """本題（特別レース名）がある場合はそれが使用される."""
        from sync_jvlink import parse_ra_record

        # 本題あり（京成杯）+ 条件コードあり
        data = "RA" + "0" * 9
        data += "20260118"
        data += "06"
        data += "01"
        data += "07"
        data += "11"
        data += "0" * 5
        # 本題に「京成杯」を設定
        name_field = "京成杯".ljust(60, "\u3000")[:60]
        data += name_field
        data += "0" * 415
        data += "12"           # SyubetuCd: 3歳
        data += "0" * 7
        data += "999"          # JyokenCd: オープン
        data += "0" * 39
        data += "2000"
        data += "0" * 172
        data += "1530"
        data += "0" * 395

        result = parse_ra_record(data)

        assert result is not None
        assert result["race_name"] == "京成杯"  # 条件名ではなく本題が使用される
