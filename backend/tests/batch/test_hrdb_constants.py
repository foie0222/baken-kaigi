"""HRDB定数・コード変換モジュールのテスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.hrdb_constants import VENUE_CODE_MAP, hrdb_to_race_id


class TestHrdbToRaceId:
    """hrdb_to_race_id のテスト."""

    def test_東京5R(self):
        assert hrdb_to_race_id("20260214", "05", "05") == "202602140505"

    def test_京都11R(self):
        assert hrdb_to_race_id("20260215", "08", "11") == "202602150811"

    def test_小倉1R(self):
        assert hrdb_to_race_id("20260214", "10", "01") == "202602141001"


class TestVenueCodeMap:
    """VENUE_CODE_MAP のテスト."""

    def test_全10場のマッピング(self):
        assert VENUE_CODE_MAP["01"] == "札幌"
        assert VENUE_CODE_MAP["05"] == "東京"
        assert VENUE_CODE_MAP["08"] == "京都"
        assert VENUE_CODE_MAP["10"] == "小倉"
        assert len(VENUE_CODE_MAP) == 10
