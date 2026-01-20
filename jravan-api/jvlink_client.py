"""JV-Link COM クライアント.

JV-Link (32bit COM) を Python から呼び出すラッパー。
Windows + Python 32bit 環境でのみ動作。
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Generator

import pythoncom
import win32com.client

logger = logging.getLogger(__name__)


class JVDataSpec(Enum):
    """JV-Link データ種別."""

    # セットアップ用
    RACE = "RACE"  # レース情報（週次）
    DIFF = "DIFF"  # 差分データ

    # リアルタイム用
    RACELIST = "0B12"  # 開催レース一覧
    RACE_INFO = "0B15"  # レース詳細
    ODDS_WIN = "0B31"  # 単勝オッズ
    ODDS_PLACE = "0B32"  # 複勝オッズ
    ODDS_WIDE = "0B35"  # ワイドオッズ
    ODDS_QUINELLA = "0B33"  # 馬連オッズ
    ODDS_EXACTA = "0B34"  # 馬単オッズ
    ODDS_TRIO = "0B36"  # 三連複オッズ
    ODDS_TRIFECTA = "0B30"  # 三連単オッズ


class JVRecordType(Enum):
    """JV-Link レコード種別."""

    RA = "RA"  # レース詳細
    SE = "SE"  # 出走馬情報
    HR = "HR"  # 払戻情報
    H1 = "H1"  # 馬毎レース情報
    O1 = "O1"  # 単勝オッズ
    O2 = "O2"  # 複勝オッズ
    O3 = "O3"  # 馬連オッズ
    O4 = "O4"  # ワイドオッズ
    O5 = "O5"  # 馬単オッズ
    O6 = "O6"  # 三連複オッズ
    WF = "WF"  # 重勝オッズ


@dataclass
class RaceInfo:
    """レース情報."""

    race_id: str
    race_name: str
    race_number: int
    venue: str
    venue_name: str
    start_time: datetime
    distance: int
    track_type: str  # 芝/ダート
    track_condition: str  # 良/稍重/重/不良
    grade: str  # G1/G2/G3/OP/条件


@dataclass
class RunnerInfo:
    """出走馬情報."""

    horse_number: int
    horse_name: str
    horse_id: str
    jockey_name: str
    jockey_id: str
    trainer_name: str
    weight: float
    odds: float | None
    popularity: int | None


class JVLinkClient:
    """JV-Link COM クライアント."""

    def __init__(self, sid: str = "BAKENKAIGI"):
        """初期化.

        Args:
            sid: ソフト ID（任意の英数字文字列、空文字は不可）
        """
        self._sid = sid
        self._jvlink = None
        self._initialized = False

    def __enter__(self):
        """コンテキストマネージャー開始."""
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了."""
        self.close()

    def init(self) -> bool:
        """JV-Link を初期化する."""
        try:
            # スレッドごとに COM を初期化
            pythoncom.CoInitialize()
            self._jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
            result = self._jvlink.JVInit(self._sid)
            if result != 0:
                logger.error(f"JVInit failed with code: {result}")
                return False
            self._initialized = True
            logger.info("JV-Link initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize JV-Link: {e}")
            return False

    def close(self):
        """JV-Link を終了する."""
        if self._jvlink:
            try:
                self._jvlink.JVClose()
            except Exception as e:
                logger.warning(f"Error closing JV-Link: {e}")
            self._jvlink = None
            self._initialized = False
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    def open_realtime(self, data_spec: str) -> int:
        """リアルタイムデータを開く.

        Args:
            data_spec: データ種別（例: "0B12"）

        Returns:
            0: 成功, 負数: エラー
        """
        if not self._initialized:
            raise RuntimeError("JV-Link is not initialized")

        # JVRTOpen(dataspec, key) - key は "" で全データ
        result = self._jvlink.JVRTOpen(data_spec, "")
        logger.debug(f"JVRTOpen({data_spec}) = {result}")
        return result

    def open_setup(self, data_spec: str, from_time: str = "00000000000000") -> int:
        """セットアップ/蓄積データを開く.

        Args:
            data_spec: データ種別（例: "RACE"）
            from_time: 取得開始日時（YYYYMMDDHHmmss）

        Returns:
            0: 成功, 正数: ダウンロード件数, 負数: エラー
        """
        if not self._initialized:
            raise RuntimeError("JV-Link is not initialized")

        # JVOpen(dataspec, fromtime, option)
        # option: 1=通常, 2=今週データ, 3=セットアップ, 4=ダイアログ表示
        result = self._jvlink.JVOpen(data_spec, from_time, 1)
        logger.debug(f"JVOpen({data_spec}, {from_time}) = {result}")
        # result は (status, count, downloaded, lastupdate) のタプル
        if isinstance(result, tuple):
            return result[0]  # status を返す
        return result

    def read(self) -> tuple[int, str, str]:
        """データを1件読み込む.

        Returns:
            (status, record_type, data)
            status: 0=EOF, 正数=データあり, -1=ダウンロード中, 負数=エラー
        """
        if not self._initialized:
            raise RuntimeError("JV-Link is not initialized")

        buff = " " * 100000  # 十分なバッファ
        result = self._jvlink.JVRead(buff, len(buff), "")

        # result は (data_length, data, buffer_size, filename) のタプル
        # data_length: 正=データあり, 0=EOF, -1=ダウンロード中, 負数=エラー
        status = result[0]
        data = result[1] if len(result) > 1 else ""

        # レコード種別はデータの先頭2文字
        record_type = data[:2] if data else ""

        return status, record_type, data

    def read_all(self) -> Generator[tuple[str, str], None, None]:
        """全データを読み込む.

        Yields:
            (record_type, data)
        """
        import time
        count = 0
        while True:
            status, record_type, data = self.read()
            count += 1
            if count <= 5 or count % 500 == 0:
                logger.info(f"read_all: count={count}, status={status}, type={record_type}")
            if status == 0:  # EOF
                logger.info(f"read_all: EOF at {count}")
                break
            if status == -1:  # ダウンロード中
                time.sleep(0.1)
                continue
            if status == -3:  # ファイルダウンロード中
                time.sleep(0.5)
                continue
            if status < 0:  # エラー
                logger.error(f"JVRead error: {status}")
                break
            yield record_type, data

    def get_race_list(self, date: str) -> list[RaceInfo]:
        """指定日のレース一覧を取得する.

        Args:
            date: 日付（YYYYMMDD）

        Returns:
            レース情報のリスト
        """
        races = []

        # 蓄積データを開く（指定日から検索）
        from_time = f"{date}000000"
        result = self.open_setup("RACE", from_time)
        if result < 0:
            logger.error(f"Failed to open race list: {result}")
            return races

        logger.info(f"JVOpen returned: {result} records")

        for record_type, data in self.read_all():
            if record_type == "RA":  # レース詳細
                race = self._parse_race_record(data)
                if race and race.race_id.startswith(date):
                    races.append(race)

        # JVClose は呼ばない（サーバー終了時に呼ぶ）
        return races

    def get_runners(self, race_id: str) -> list[RunnerInfo]:
        """出走馬情報を取得する.

        Args:
            race_id: レース ID

        Returns:
            出走馬情報のリスト
        """
        runners = []

        result = self.open_realtime("0B15")  # レース詳細
        if result < 0:
            logger.error(f"Failed to open race info: {result}")
            return runners

        for record_type, data in self.read_all():
            if record_type == "SE":  # 出走馬情報
                runner = self._parse_runner_record(data)
                if runner:
                    runners.append(runner)

        return runners

    def _parse_race_record(self, data: str) -> RaceInfo | None:
        """RA レコードをパースする.

        JV-Data 仕様書に基づく固定長レコード。
        """
        try:
            # 固定長レコードのパース
            record_type = data[0:2]  # レコード種別
            if record_type != "RA":
                return None

            # データ区分
            data_div = data[2:3]

            # [3:11] 作成日時
            # [11:19] 開催日（YYYYMMDD）
            race_date = data[11:19]

            # [19:21] 場所コード
            jyo_cd = data[19:21]

            # [21:23] 開催回
            kai = data[21:23]

            # [23:25] 日目
            nichiji = data[23:25]

            # [25:27] レース番号
            race_num = data[25:27]

            # レース ID（開催日+場所+回+日目+レース番号）
            race_id = f"{race_date}{jyo_cd}{kai}{nichiji}{race_num}"

            # レース名は後ろの方にある（仮で空文字）
            race_name = f"{jyo_cd}場 {int(race_num)}R"

            # 場所名
            venue_names = {
                "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
                "05": "東京", "06": "中山", "07": "中京", "08": "京都",
                "09": "阪神", "10": "小倉",
            }
            venue_name = venue_names.get(jyo_cd, "不明")
            race_name = f"{venue_name} {int(race_num)}R"

            # 発走時刻（仮で12:00）
            year = race_date[:4]
            month = race_date[4:6]
            day = race_date[6:8]
            start_time_str = f"{year}-{month}-{day} 12:00"

            return RaceInfo(
                race_id=race_id,
                race_name=race_name,
                race_number=int(race_num),
                venue=jyo_cd,
                venue_name=venue_name,
                start_time=datetime.strptime(start_time_str, "%Y-%m-%d %H:%M"),
                distance=0,  # 別途パース
                track_type="",
                track_condition="",
                grade="",  # 別途パース
            )
        except Exception as e:
            logger.error(f"Failed to parse RA record: {e}")
            return None

    def _parse_runner_record(self, data: str) -> RunnerInfo | None:
        """SE レコードをパースする."""
        try:
            record_type = data[0:2]
            if record_type != "SE":
                return None

            # 馬番
            horse_number = int(data[2:4])

            # 馬名（36バイト、Shift_JIS）
            horse_name = data[4:40].strip()

            # 馬ID
            horse_id = data[40:50].strip()

            # 騎手名（12バイト）
            jockey_name = data[50:62].strip()

            # 騎手ID
            jockey_id = data[62:67].strip()

            # 調教師名
            trainer_name = data[67:79].strip()

            # 馬体重
            weight_str = data[79:82]
            weight = float(weight_str) if weight_str.strip() else 0.0

            return RunnerInfo(
                horse_number=horse_number,
                horse_name=horse_name,
                horse_id=horse_id,
                jockey_name=jockey_name,
                jockey_id=jockey_id,
                trainer_name=trainer_name,
                weight=weight,
                odds=None,  # 別途取得
                popularity=None,
            )
        except Exception as e:
            logger.error(f"Failed to parse SE record: {e}")
            return None
