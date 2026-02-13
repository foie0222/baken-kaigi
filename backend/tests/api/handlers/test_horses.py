"""馬API ハンドラーのテスト."""
import json

from src.api.handlers.horses import (
    get_course_aptitude,
    get_extended_pedigree,
    get_horse_performances,
    get_horse_training,
)


class TestGetHorsePerformances:
    """get_horse_performances のテスト."""

    def test_正常取得(self) -> None:
        """馬の過去成績を正常に取得できる."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_horse_performances(event, None)
        assert response["statusCode"] == 200
        body = response.get("body")
        assert body is not None
        data = json.loads(body)
        assert "horse_id" in data
        assert "horse_name" in data
        assert "performances" in data
        assert isinstance(data["performances"], list)

    def test_limitパラメータ(self) -> None:
        """limit パラメータでレコード数を制限できる."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"limit": "3"},
        }
        response = get_horse_performances(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert len(data["performances"]) <= 3

    def test_無効なlimit(self) -> None:
        """limit が無効な場合はエラーを返す."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"limit": "abc"},
        }
        response = get_horse_performances(event, None)
        assert response["statusCode"] == 400

    def test_limit範囲外(self) -> None:
        """limit が範囲外の場合はエラーを返す."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"limit": "25"},
        }
        response = get_horse_performances(event, None)
        assert response["statusCode"] == 400

    def test_track_typeフィルタ(self) -> None:
        """track_type でフィルタできる."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"track_type": "芝"},
        }
        response = get_horse_performances(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        for perf in data["performances"]:
            assert perf["track_type"] == "芝"

    def test_無効なtrack_type(self) -> None:
        """track_type が無効な場合はエラーを返す."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"track_type": "砂"},
        }
        response = get_horse_performances(event, None)
        assert response["statusCode"] == 400

    def test_horse_id未指定(self) -> None:
        """horse_id が指定されていない場合はエラーを返す."""
        event = {
            "pathParameters": {},
            "queryStringParameters": None,
        }
        response = get_horse_performances(event, None)
        assert response["statusCode"] == 400


class TestGetHorseTraining:
    """get_horse_training のテスト."""

    def test_正常取得(self) -> None:
        """馬の調教データを正常に取得できる."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 200
        body = response.get("body")
        assert body is not None
        data = json.loads(body)
        assert "horse_id" in data
        assert "horse_name" in data
        assert "training_records" in data
        assert "training_summary" in data
        assert isinstance(data["training_records"], list)

    def test_limitパラメータ(self) -> None:
        """limit パラメータでレコード数を制限できる."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"limit": "3"},
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert len(data["training_records"]) <= 3

    def test_無効なlimit(self) -> None:
        """limit が無効な場合はエラーを返す."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"limit": "abc"},
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 400

    def test_limit範囲外(self) -> None:
        """limit が範囲外の場合はエラーを返す."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"limit": "15"},
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 400

    def test_daysパラメータ(self) -> None:
        """days パラメータで対象期間を指定できる."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"days": "14"},
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert isinstance(data["training_records"], list)

    def test_無効なdays(self) -> None:
        """days が無効な場合はエラーを返す."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"days": "abc"},
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 400

    def test_days範囲外(self) -> None:
        """days が範囲外の場合はエラーを返す."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": {"days": "500"},
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 400

    def test_horse_id未指定(self) -> None:
        """horse_id が指定されていない場合はエラーを返す."""
        event = {
            "pathParameters": {},
            "queryStringParameters": None,
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 400

    def test_training_recordsの構造(self) -> None:
        """training_records の各レコードが必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        if data["training_records"]:
            record = data["training_records"][0]
            assert "date" in record
            assert "course" in record
            assert "course_condition" in record
            assert "distance" in record
            assert "time" in record
            assert "evaluation" in record

    def test_training_summaryの構造(self) -> None:
        """training_summary が必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_horse_training(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        if data["training_summary"]:
            summary = data["training_summary"]
            assert "recent_trend" in summary
            assert "average_time" in summary
            assert "best_time" in summary


class TestGetExtendedPedigree:
    """get_extended_pedigree のテスト."""

    def test_正常取得(self) -> None:
        """馬の拡張血統情報を正常に取得できる."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_extended_pedigree(event, None)
        assert response["statusCode"] == 200
        body = response.get("body")
        assert body is not None
        data = json.loads(body)
        assert "horse_id" in data
        assert "horse_name" in data
        assert "sire" in data
        assert "dam" in data
        assert "inbreeding" in data
        assert "lineage_type" in data

    def test_horse_id未指定(self) -> None:
        """horse_id が指定されていない場合はエラーを返す."""
        event = {
            "pathParameters": {},
            "queryStringParameters": None,
        }
        response = get_extended_pedigree(event, None)
        assert response["statusCode"] == 400

    def test_sireの構造(self) -> None:
        """sire が必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_extended_pedigree(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        if data["sire"]:
            sire = data["sire"]
            assert "name" in sire
            assert "sire" in sire
            assert "dam" in sire
            assert "broodmare_sire" in sire

    def test_damの構造(self) -> None:
        """dam が必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_extended_pedigree(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        if data["dam"]:
            dam = data["dam"]
            assert "name" in dam
            assert "sire" in dam
            assert "dam" in dam
            assert "broodmare_sire" in dam

    def test_inbreedingの構造(self) -> None:
        """inbreeding の各レコードが必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_extended_pedigree(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert isinstance(data["inbreeding"], list)
        for inbreeding in data["inbreeding"]:
            assert "ancestor" in inbreeding
            assert "pattern" in inbreeding
            assert "percentage" in inbreeding

    def test_存在しない馬で404(self) -> None:
        """存在しない馬の場合は404を返す."""
        event = {
            "pathParameters": {"horse_id": "nonexistent_horse"},
            "queryStringParameters": None,
        }
        response = get_extended_pedigree(event, None)
        assert response["statusCode"] == 404


class TestGetCourseAptitude:
    """get_course_aptitude のテスト."""

    def test_正常取得(self) -> None:
        """馬のコース適性を正常に取得できる."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 200
        body = response.get("body")
        assert body is not None
        data = json.loads(body)
        assert "horse_id" in data
        assert "horse_name" in data
        assert "by_venue" in data
        assert "by_track_type" in data
        assert "by_distance" in data
        assert "by_track_condition" in data
        assert "by_running_position" in data
        assert "aptitude_summary" in data

    def test_horse_id未指定(self) -> None:
        """horse_id が指定されていない場合はエラーを返す."""
        event = {
            "pathParameters": {},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 400

    def test_存在しない馬で404(self) -> None:
        """存在しない馬の場合は404を返す."""
        event = {
            "pathParameters": {"horse_id": "nonexistent_horse"},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 404

    def test_by_venueの構造(self) -> None:
        """by_venue の各レコードが必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert isinstance(data["by_venue"], list)
        for venue in data["by_venue"]:
            assert "venue" in venue
            assert "starts" in venue
            assert "wins" in venue
            assert "places" in venue
            assert "win_rate" in venue
            assert "place_rate" in venue

    def test_by_track_typeの構造(self) -> None:
        """by_track_type の各レコードが必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert isinstance(data["by_track_type"], list)
        for tt in data["by_track_type"]:
            assert "track_type" in tt
            assert "starts" in tt
            assert "wins" in tt
            assert "win_rate" in tt

    def test_by_distanceの構造(self) -> None:
        """by_distance の各レコードが必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert isinstance(data["by_distance"], list)
        for dist in data["by_distance"]:
            assert "distance_range" in dist
            assert "starts" in dist
            assert "wins" in dist
            assert "win_rate" in dist

    def test_by_track_conditionの構造(self) -> None:
        """by_track_condition の各レコードが必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert isinstance(data["by_track_condition"], list)
        for cond in data["by_track_condition"]:
            assert "condition" in cond
            assert "starts" in cond
            assert "wins" in cond
            assert "win_rate" in cond

    def test_by_running_positionの構造(self) -> None:
        """by_running_position の各レコードが必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert isinstance(data["by_running_position"], list)
        for pos in data["by_running_position"]:
            assert "position" in pos
            assert "starts" in pos
            assert "wins" in pos
            assert "win_rate" in pos

    def test_aptitude_summaryの構造(self) -> None:
        """aptitude_summary が必要なフィールドを持つ."""
        event = {
            "pathParameters": {"horse_id": "horse_0001"},
            "queryStringParameters": None,
        }
        response = get_course_aptitude(event, None)
        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        if data["aptitude_summary"]:
            summary = data["aptitude_summary"]
            assert "best_venue" in summary
            assert "best_distance" in summary
            assert "preferred_condition" in summary
            assert "preferred_position" in summary
