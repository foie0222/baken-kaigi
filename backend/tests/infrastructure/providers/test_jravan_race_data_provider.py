"""JraVanRaceDataProviderのテスト."""

from unittest.mock import MagicMock, patch

from src.infrastructure.providers.jravan_race_data_provider import (
    JraVanRaceDataProvider,
)


class TestGetPastRaceStats:
    """get_past_race_statsメソッドのテスト."""

    def test_正常なAPIレスポンスでPastRaceStatsを返す(self):
        provider = JraVanRaceDataProvider(base_url="http://test:8000")

        with patch.object(provider._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "total_races": 100,
                "popularity_stats": [
                    {
                        "popularity": 1,
                        "total_runs": 100,
                        "wins": 33,
                        "places": 60,
                        "win_rate": 33.0,
                        "place_rate": 60.0,
                    }
                ],
                "avg_win_payout": 350.5,
                "avg_place_payout": 180.2,
                "conditions": {
                    "track_code": "1",
                    "distance": 1600,
                    "grade_code": None,
                },
            }
            mock_get.return_value = mock_response

            result = provider.get_past_race_stats(
                track_type="芝",
                distance=1600,
                grade_class=None,
                limit=100,
            )

            assert result is not None
            assert result.total_races == 100
            assert len(result.popularity_stats) == 1
            assert result.popularity_stats[0].popularity == 1
            assert result.popularity_stats[0].win_rate == 33.0
            assert result.avg_win_payout == 350.5
            assert result.distance == 1600

    def test_404レスポンスでNoneを返す(self):
        provider = JraVanRaceDataProvider(base_url="http://test:8000")

        with patch.object(provider._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = provider.get_past_race_stats(
                track_type="芝",
                distance=9999,
                grade_class=None,
                limit=100,
            )

            assert result is None

    def test_APIエラーでNoneを返す(self):
        import requests as real_requests

        provider = JraVanRaceDataProvider(base_url="http://test:8000")

        with patch.object(provider._session, "get") as mock_get:
            mock_get.side_effect = real_requests.RequestException("Connection error")

            result = provider.get_past_race_stats(
                track_type="芝",
                distance=1600,
                grade_class=None,
                limit=100,
            )

            assert result is None


class TestToTrackCode:
    """_to_track_codeメソッドのテスト."""

    def test_芝はコード1を返す(self):
        provider = JraVanRaceDataProvider(base_url="http://test:8000")
        assert provider._to_track_code("芝") == "1"

    def test_ダートはコード2を返す(self):
        provider = JraVanRaceDataProvider(base_url="http://test:8000")
        assert provider._to_track_code("ダート") == "2"

    def test_障害はコード3を返す(self):
        provider = JraVanRaceDataProvider(base_url="http://test:8000")
        assert provider._to_track_code("障害") == "3"
