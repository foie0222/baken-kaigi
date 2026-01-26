"""レース結果API ハンドラーテスト."""
from unittest.mock import MagicMock

import pytest

from src.api.handlers.races import get_race_results
from src.domain.ports import PayoutData, RaceResultData, RaceResultsData


@pytest.fixture
def mock_provider(monkeypatch):
    """モックプロバイダーをセットアップする."""
    mock = MagicMock()
    monkeypatch.setattr(
        "src.api.handlers.races.Dependencies.get_race_data_provider",
        lambda: mock,
    )
    return mock


class TestGetRaceResults:
    """get_race_results ハンドラーのテスト."""

    def test_race_idがない場合は400を返す(self, mock_provider):
        """race_idがない場合は400エラーを返す."""
        event = {"pathParameters": {}}
        result = get_race_results(event, None)
        assert result["statusCode"] == 400

    def test_結果が見つからない場合は404を返す(self, mock_provider):
        """レース結果が見つからない場合は404を返す."""
        mock_provider.get_race_results.return_value = None
        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_race_results(event, None)
        assert result["statusCode"] == 404

    def test_正常なレース結果を返す(self, mock_provider):
        """正常なレース結果を返す."""
        mock_provider.get_race_results.return_value = RaceResultsData(
            race_id="202401010101",
            race_name="テストレース",
            race_date="2024-01-01",
            venue="東京",
            results=[
                RaceResultData(
                    horse_number=1,
                    horse_name="テスト馬",
                    finish_position=1,
                    time="1:33.5",
                    margin=None,
                    last_3f="33.8",
                    popularity=2,
                    odds=3.5,
                    jockey_name="テスト騎手",
                ),
            ],
            payouts=[
                PayoutData(
                    bet_type="単勝",
                    combination="1",
                    payout=350,
                    popularity=2,
                ),
            ],
            is_finalized=True,
        )

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_race_results(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert body["race_id"] == "202401010101"
        assert body["race_name"] == "テストレース"
        assert body["is_finalized"] is True
        assert len(body["results"]) == 1
        assert body["results"][0]["horse_number"] == 1
        assert body["results"][0]["horse_name"] == "テスト馬"
        assert body["results"][0]["finish_position"] == 1
        assert body["results"][0]["time"] == "1:33.5"
        assert len(body["payouts"]) == 1
        assert body["payouts"][0]["bet_type"] == "単勝"
        assert body["payouts"][0]["payout"] == 350

    def test_複数の結果と払戻を返す(self, mock_provider):
        """複数の着順結果と払戻金を返す."""
        mock_provider.get_race_results.return_value = RaceResultsData(
            race_id="202401010101",
            race_name="テストレース",
            race_date="2024-01-01",
            venue="東京",
            results=[
                RaceResultData(
                    horse_number=3,
                    horse_name="一着馬",
                    finish_position=1,
                    time="1:33.5",
                    margin=None,
                    last_3f="33.8",
                    popularity=1,
                    odds=2.5,
                    jockey_name="騎手A",
                ),
                RaceResultData(
                    horse_number=5,
                    horse_name="二着馬",
                    finish_position=2,
                    time="1:33.7",
                    margin="クビ",
                    last_3f="34.0",
                    popularity=3,
                    odds=5.5,
                    jockey_name="騎手B",
                ),
                RaceResultData(
                    horse_number=7,
                    horse_name="三着馬",
                    finish_position=3,
                    time="1:33.9",
                    margin="1/2",
                    last_3f="34.2",
                    popularity=2,
                    odds=4.0,
                    jockey_name="騎手C",
                ),
            ],
            payouts=[
                PayoutData(bet_type="単勝", combination="3", payout=250, popularity=1),
                PayoutData(bet_type="複勝", combination="3", payout=120, popularity=1),
                PayoutData(bet_type="複勝", combination="5", payout=180, popularity=3),
                PayoutData(bet_type="複勝", combination="7", payout=150, popularity=2),
                PayoutData(bet_type="馬連", combination="3-5", payout=1200, popularity=2),
                PayoutData(bet_type="三連複", combination="3-5-7", payout=2500, popularity=1),
            ],
            is_finalized=True,
        )

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_race_results(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert len(body["results"]) == 3
        assert body["results"][1]["margin"] == "クビ"
        assert len(body["payouts"]) == 6

    def test_未確定のレース結果を返す(self, mock_provider):
        """未確定のレース結果でis_finalizedがFalseを返す."""
        mock_provider.get_race_results.return_value = RaceResultsData(
            race_id="202401010101",
            race_name="テストレース",
            race_date="2024-01-01",
            venue="東京",
            results=[],
            payouts=[],
            is_finalized=False,
        )

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_race_results(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert body["is_finalized"] is False
