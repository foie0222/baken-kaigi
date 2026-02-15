"""JraVanRaceDataProviderのテスト."""

from unittest.mock import MagicMock, patch

from src.domain.identifiers import RaceId
from src.domain.ports import AllOddsData
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


class TestGetAllOdds:
    """get_all_oddsメソッドのテスト."""

    def test_正常なAPIレスポンスでAllOddsDataを返す(self):
        """全券種オッズを正常に取得できることを確認."""
        provider = JraVanRaceDataProvider(base_url="http://test:8000")

        with patch.object(provider._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "race_id": "2024060111",
                "win": {"1": 3.5, "3": 5.5},
                "place": {"1": {"min": 1.2, "max": 2.0}, "3": {"min": 2.0, "max": 3.5}},
                "quinella": {"1-3": 15.2},
                "quinella_place": {"1-3": 5.0},
                "exacta": {"1-3": 25.0},
                "trio": {"1-3-5": 80.0},
                "trifecta": {"1-3-5": 350.0},
            }
            mock_get.return_value = mock_response

            result = provider.get_all_odds(race_id=RaceId("2024060111"))

            assert result is not None
            assert isinstance(result, AllOddsData)
            assert result.race_id == "2024060111"
            assert result.win == {"1": 3.5, "3": 5.5}
            assert result.place == {"1": {"min": 1.2, "max": 2.0}, "3": {"min": 2.0, "max": 3.5}}
            assert result.quinella == {"1-3": 15.2}
            assert result.quinella_place == {"1-3": 5.0}
            assert result.exacta == {"1-3": 25.0}
            assert result.trio == {"1-3-5": 80.0}
            assert result.trifecta == {"1-3-5": 350.0}

            mock_get.assert_called_once_with(
                "http://test:8000/races/2024060111/odds",
                timeout=30,
            )

    def test_200以外のステータスコードでNoneを返す(self):
        """APIが200以外を返した場合にNoneを返すことを確認."""
        provider = JraVanRaceDataProvider(base_url="http://test:8000")

        with patch.object(provider._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = provider.get_all_odds(race_id=RaceId("2024060111"))

            assert result is None

    def test_APIエラーでNoneを返す(self):
        """APIへの接続エラー時にNoneを返すことを確認."""
        import requests as real_requests

        provider = JraVanRaceDataProvider(base_url="http://test:8000")

        with patch.object(provider._session, "get") as mock_get:
            mock_get.side_effect = real_requests.RequestException("Connection error")

            result = provider.get_all_odds(race_id=RaceId("2024060111"))

            assert result is None
