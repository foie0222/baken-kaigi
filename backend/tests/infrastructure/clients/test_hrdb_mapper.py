"""HRDB→DynamoDBマッピングのテスト."""
import pytest

from src.infrastructure.clients.hrdb_mapper import (
    map_horse_to_horse_item,
    map_jky_to_jockey_item,
    map_racedtl_to_runner_item,
    map_racemst_to_race_item,
    map_trnr_to_trainer_item,
)


class TestMapRacemstToRaceItem:
    def test_正常系_RACEMSTレコードをracesテーブルアイテムに変換する(self):
        row = {
            "OPDT": "20260215",
            "RCOURSECD": "06",
            "RNO": "11",
            "RNAME": "フェブラリーS",
            "TRACKCD": "23",
            "KYORI": "1600",
            "TENKO": "1",
            "SHIBA_DART_CD": "2",
            "BABA": "1",
            "TOSU": "16",
            "GRADECD": "1",
            "JYOKENCD": "A3",
            "HTIME": "1540",
        }
        item = map_racemst_to_race_item(row)
        assert item["race_date"] == "20260215"
        assert item["race_id"] == "20260215_06_11"
        assert item["race_name"] == "フェブラリーS"
        assert item["distance"] == 1600
        assert item["horse_count"] == 16
        assert item["race_number"] == 11
        assert item["venue_code"] == "06"
        assert item["grade_code"] == "1"

    def test_RNOが1桁の場合もrace_idが正しく生成される(self):
        row = {
            "OPDT": "20260215",
            "RCOURSECD": "06",
            "RNO": "1",
            "RNAME": "1R",
            "KYORI": "1200",
            "TOSU": "10",
        }
        item = map_racemst_to_race_item(row)
        assert item["race_id"] == "20260215_06_01"


class TestMapRacedtlToRunnerItem:
    def test_正常系_RACEDTLレコードをrunnersテーブルアイテムに変換する(self):
        row = {
            "OPDT": "20260215",
            "RCOURSECD": "06",
            "RNO": "11",
            "UMABAN": "3",
            "BAMEI": "テスト馬",
            "BLDNO": "2020100001",
            "JKYCD": "01234",
            "JKYNAME": "テスト騎手",
            "TRNRCD": "05678",
            "ODDS": "5.6",
            "NINKI": "2",
            "WAKUBAN": "2",
            "FUTAN": "57.0",
            "KAKUTEI": "1",
            "TIME": "1335",
            "AGARI3F": "345",
        }
        item = map_racedtl_to_runner_item(row)
        assert item["race_id"] == "20260215_06_11"
        assert item["horse_number"] == 3
        assert item["horse_name"] == "テスト馬"
        assert item["horse_id"] == "2020100001"
        assert item["jockey_id"] == "01234"
        from decimal import Decimal
        assert item["odds"] == Decimal("5.6")
        assert item["finish_position"] == 1
        assert item["race_date"] == "20260215"


class TestMapHorseToHorseItem:
    def test_正常系_HORSEレコードをhorsesテーブルアイテムに変換する(self):
        row = {
            "BLDNO": "2020100001",
            "BAMEI": "テスト馬",
            "FTNAME": "ディープインパクト",
            "MTNAME": "テスト母馬",
            "BMSTNAME": "キングカメハメハ",
            "BNEN": "2020",
            "SEX": "1",
            "KEIRO": "01",
        }
        item = map_horse_to_horse_item(row)
        assert item["horse_id"] == "2020100001"
        assert item["sk"] == "info"
        assert item["horse_name"] == "テスト馬"
        assert item["sire_name"] == "ディープインパクト"
        assert item["dam_name"] == "テスト母馬"
        assert item["broodmare_sire"] == "キングカメハメハ"


class TestMapJkyToJockeyItem:
    def test_正常系_JKYレコードをjockeysテーブルアイテムに変換する(self):
        row = {
            "JKYCD": "01234",
            "JKYNAME": "テスト騎手",
            "JKYKANA": "テストキシュ",
            "SHOZOKU": "美浦",
        }
        item = map_jky_to_jockey_item(row)
        assert item["jockey_id"] == "01234"
        assert item["sk"] == "info"
        assert item["jockey_name"] == "テスト騎手"
        assert item["affiliation"] == "美浦"


class TestMapTrnrToTrainerItem:
    def test_正常系_TRNRレコードをtrainersテーブルアイテムに変換する(self):
        row = {
            "TRNRCD": "05678",
            "TRNRNAME": "テスト調教師",
            "TRNRKANA": "テストチョウキョウシ",
            "SHOZOKU": "栗東",
        }
        item = map_trnr_to_trainer_item(row)
        assert item["trainer_id"] == "05678"
        assert item["sk"] == "info"
        assert item["trainer_name"] == "テスト調教師"
        assert item["affiliation"] == "栗東"
