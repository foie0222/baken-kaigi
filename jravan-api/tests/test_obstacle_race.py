"""障害レースの判定ロジックのテスト."""
from database import _to_race_dict, AGE_CONDITION_MAP, OBSTACLE_SHUBETSU_CODES


def _make_row(**overrides):
    """テスト用のレースデータ行を作成する."""
    base = {
        "kaisai_nen": "2026",
        "kaisai_tsukihi": "0214",
        "keibajo_code": "10",
        "race_bango": "04",
        "kyosomei_hondai": "",
        "kyosomei_fukudai": "",
        "grade_code": "",
        "kyori": "2860",
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


class Test_track_codeによる障害判定:
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


class Test_競走種別コードによる障害フォールバック:
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

    def test_track_code_1xならshubetsu_21でも芝が優先(self):
        """track_codeが設定されている場合はtrack_codeが優先される."""
        row = _make_row(track_code="11", kyoso_shubetsu_code="21")
        result = _to_race_dict(row)
        assert result["track_type"] == "芝"
        # ただしis_obstacleはshubetsu_codeで判定される
        assert result["is_obstacle"] is True


class Test_障害レースの年齢条件:
    def test_shubetsu_21は3歳以上(self):
        assert AGE_CONDITION_MAP["21"] == "3歳以上"

    def test_shubetsu_22は4歳以上(self):
        assert AGE_CONDITION_MAP["22"] == "4歳以上"

    def test_障害レースで年齢条件が返る(self):
        row = _make_row(track_code="", kyoso_shubetsu_code="22")
        result = _to_race_dict(row)
        assert result["age_condition"] == "4歳以上"
        assert result["is_obstacle"] is True


class Test_OBSTACLE_SHUBETSU_CODES:
    def test_21から29まで含まれる(self):
        for code in ["21", "22", "23", "24", "25", "26", "27", "28", "29"]:
            assert code in OBSTACLE_SHUBETSU_CODES

    def test_平地コードは含まれない(self):
        for code in ["11", "12", "13", "14"]:
            assert code not in OBSTACLE_SHUBETSU_CODES
