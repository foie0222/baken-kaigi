"""馬API ハンドラーのテスト."""
import pytest

from src.api.handlers.horses import get_horse_performances


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
        import json
        data = json.loads(body)
        assert "horse_id" in data
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
        import json
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
        import json
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
