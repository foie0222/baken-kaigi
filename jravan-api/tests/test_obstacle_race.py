"""障害レースの判定ロジックのテスト."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# pg8000 のモックを追加（Linuxテスト環境用）
mock_pg8000 = MagicMock()
sys.modules['pg8000'] = mock_pg8000

# テスト対象モジュールへのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import _to_race_dict, AGE_CONDITION_MAP, OBSTACLE_SHUBETSU_CODES


def _make_row(**overrides):
    """テスト用のレースデータ行を作成する.

    デフォルト距離は1600m（平地の標準距離）を使用。
    """
    base = {
        "kaisai_nen": "2026",
        "kaisai_tsukihi": "0214",
        "keibajo_code": "10",
        "race_bango": "04",
        "kyosomei_hondai": "",
        "kyosomei_fukudai": "",
        "grade_code": "",
        "kyori": "1600",
        "track_code": "",
        "babajotai_code_shiba": "",
        "babajotai_code_dirt": "",
        "hasso_jikoku": "1110",
        "shusso_tosu": "12",
        "kyoso_shubetsu_code": "14",
        "kyoso_joken_code": "703",
        "kaisai_kai": "01",
        "kaisai_nichime": "07",
    }
    base.update(overrides)
    return base


class TestTrackCodeObstacleDetection:
    def test_track_code_3xで障害レースと判定される(self):
        row = _make_row(track_code="31")
        result = _to_race_dict(row)
        assert result["is_obstacle"] is True
        assert result["track_type"] == "障害"

    def test_track_code_1xは芝(self):
        row = _make_row(track_code="11")
        result = _to_race_dict(row)
        assert result["is_obstacle"] is False
        assert result["track_type"] == "芝"

    def test_track_code_2xはダート(self):
        row = _make_row(track_code="23")
        result = _to_race_dict(row)
        assert result["is_obstacle"] is False
        assert result["track_type"] == "ダート"


class TestShubetsuCodeObstacleFallback:
    def test_track_code空でshubetsu_21なら障害と判定(self):
        row = _make_row(track_code="", kyoso_shubetsu_code="21")
        result = _to_race_dict(row)
        assert result["is_obstacle"] is True
        assert result["track_type"] == "障害"

    def test_track_code空でshubetsu_22なら障害と判定(self):
        row = _make_row(track_code="", kyoso_shubetsu_code="22")
        result = _to_race_dict(row)
        assert result["is_obstacle"] is True
        assert result["track_type"] == "障害"

    def test_track_code空でshubetsu_14なら平地(self):
        row = _make_row(track_code="", kyoso_shubetsu_code="14")
        result = _to_race_dict(row)
        assert result["is_obstacle"] is False
        assert result["track_type"] == ""

    def test_track_code芝でもshubetsu_21ならis_obstacleはTrue(self):
        """track_typeはtrack_codeから決定されるが、is_obstacleはshubetsu_codeでも判定される."""
        row = _make_row(track_code="11", kyoso_shubetsu_code="21")
        result = _to_race_dict(row)
        assert result["track_type"] == "芝"
        assert result["is_obstacle"] is True


class TestObstacleRaceAgeCondition:
    def test_shubetsu_21は3歳以上(self):
        assert AGE_CONDITION_MAP["21"] == "3歳以上"

    def test_shubetsu_22は4歳以上(self):
        assert AGE_CONDITION_MAP["22"] == "4歳以上"

    def test_障害レースで年齢条件が返る(self):
        row = _make_row(track_code="", kyoso_shubetsu_code="22")
        result = _to_race_dict(row)
        assert result["age_condition"] == "4歳以上"
        assert result["is_obstacle"] is True


class TestObstacleShuhetsuCodes:
    def test_21から29まで含まれる(self):
        for code in ["21", "22", "23", "24", "25", "26", "27", "28", "29"]:
            assert code in OBSTACLE_SHUBETSU_CODES

    def test_平地コードは含まれない(self):
        for code in ["11", "12", "13", "14"]:
            assert code not in OBSTACLE_SHUBETSU_CODES


class TestRaceNameObstacleFallback:
    """track_codeもshubetsu_codeも障害を示さない場合、レース名からフォールバック判定."""

    def test_レース名にジャンプを含む場合は障害と判定(self):
        row = _make_row(
            track_code="", kyoso_shubetsu_code="14",
            kyosomei_hondai="小倉ジャンプステークス",
        )
        result = _to_race_dict(row)
        assert result["is_obstacle"] is True
        assert result["track_type"] == "障害"

    def test_レース名に障害を含む場合は障害と判定(self):
        row = _make_row(
            track_code="", kyoso_shubetsu_code="14",
            kyosomei_hondai="障害未勝利",
        )
        result = _to_race_dict(row)
        assert result["is_obstacle"] is True
        assert result["track_type"] == "障害"

    def test_通常のレース名では障害判定されない(self):
        row = _make_row(
            track_code="", kyoso_shubetsu_code="14",
            kyosomei_hondai="東京優駿",
        )
        result = _to_race_dict(row)
        assert result["is_obstacle"] is False

    def test_副題にジャンプを含む場合も障害と判定(self):
        row = _make_row(
            track_code="", kyoso_shubetsu_code="14",
            kyosomei_hondai="", kyosomei_fukudai="ジャンプ特別",
        )
        result = _to_race_dict(row)
        assert result["is_obstacle"] is True
        assert result["track_type"] == "障害"

    def test_track_code芝でレース名にジャンプを含んでもフォールバックはスキップ(self):
        """track_codeが芝(1x)の場合、レース名フォールバックは適用されない."""
        row = _make_row(
            track_code="11", kyoso_shubetsu_code="14",
            kyosomei_hondai="ジャンプ大会",
        )
        result = _to_race_dict(row)
        assert result["is_obstacle"] is False
        assert result["track_type"] == "芝"
