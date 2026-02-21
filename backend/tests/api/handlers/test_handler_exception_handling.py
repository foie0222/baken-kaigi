"""全APIハンドラーのプロバイダ例外処理テスト.

プロバイダ呼び出しで例外発生時に、500レスポンスとCORSヘッダーが返ることを検証する。
"""
import pytest


def _make_provider_raise(monkeypatch, module_path: str):
    """対象ハンドラーモジュールのDependencies.get_race_data_providerを例外送出に差し替える."""
    monkeypatch.setattr(
        f"{module_path}.Dependencies.get_race_data_provider",
        lambda: (_ for _ in ()).throw(RuntimeError("DynamoDB connection error")),
    )


def _assert_500_with_cors(response: dict):
    assert response["statusCode"] == 500
    assert "Access-Control-Allow-Origin" in response["headers"]


# --- horses.py ---

class TestHorsesExceptionHandling:
    """horses.py: プロバイダ例外時に500が返る."""

    MODULE = "src.api.handlers.horses"

    def test_get_horse_performancesでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.horses import get_horse_performances

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"horse_id": "h001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_horse_performances(event, None))

    def test_get_horse_trainingでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.horses import get_horse_training

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"horse_id": "h001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_horse_training(event, None))

    def test_get_extended_pedigreeでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.horses import get_extended_pedigree

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"horse_id": "h001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_extended_pedigree(event, None))

    def test_get_course_aptitudeでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.horses import get_course_aptitude

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"horse_id": "h001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_course_aptitude(event, None))


# --- statistics.py ---

class TestStatisticsExceptionHandling:
    """statistics.py: プロバイダ例外時に500が返る."""

    MODULE = "src.api.handlers.statistics"

    def test_get_gate_position_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.statistics import get_gate_position_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"queryStringParameters": {"venue": "阪神"}}
        _assert_500_with_cors(get_gate_position_stats(event, None))

    def test_get_past_race_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.statistics import get_past_race_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"queryStringParameters": {"track_code": "1", "distance": "1600"}}
        _assert_500_with_cors(get_past_race_stats(event, None))

    def test_get_jockey_course_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.statistics import get_jockey_course_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"queryStringParameters": {"jockey_id": "j001", "track_code": "1", "distance": "1600"}}
        _assert_500_with_cors(get_jockey_course_stats(event, None))

    def test_get_popularity_payout_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.statistics import get_popularity_payout_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"queryStringParameters": {"track_code": "1", "distance": "1600", "popularity": "1"}}
        _assert_500_with_cors(get_popularity_payout_stats(event, None))


# --- jockeys.py ---

class TestJockeysExceptionHandling:
    """jockeys.py: プロバイダ例外時に500が返る."""

    MODULE = "src.api.handlers.jockeys"

    def test_get_jockey_infoでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.jockeys import get_jockey_info

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"jockey_id": "j001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_jockey_info(event, None))

    def test_get_jockey_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.jockeys import get_jockey_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"jockey_id": "j001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_jockey_stats(event, None))


# --- trainers.py ---

class TestTrainersExceptionHandling:
    """trainers.py: プロバイダ例外時に500が返る."""

    MODULE = "src.api.handlers.trainers"

    def test_get_trainer_infoでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.trainers import get_trainer_info

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"trainer_id": "t001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_trainer_info(event, None))

    def test_get_trainer_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.trainers import get_trainer_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"trainer_id": "t001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_trainer_stats(event, None))


# --- stallions.py ---

class TestStallionsExceptionHandling:
    """stallions.py: プロバイダ例外時に500が返る."""

    MODULE = "src.api.handlers.stallions"

    def test_get_stallion_offspring_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.stallions import get_stallion_offspring_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"stallion_id": "s001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_stallion_offspring_stats(event, None))


# --- owners.py ---

class TestOwnersExceptionHandling:
    """owners.py: プロバイダ例外時に500が返る."""

    MODULE = "src.api.handlers.owners"

    def test_get_owner_infoでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.owners import get_owner_info

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"owner_id": "o001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_owner_info(event, None))

    def test_get_owner_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.owners import get_owner_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"owner_id": "o001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_owner_stats(event, None))

    def test_get_breeder_infoでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.owners import get_breeder_info

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"breeder_id": "b001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_breeder_info(event, None))

    def test_get_breeder_statsでプロバイダ例外時に500(self, monkeypatch):
        from src.api.handlers.owners import get_breeder_stats

        _make_provider_raise(monkeypatch, self.MODULE)
        event = {"pathParameters": {"breeder_id": "b001"}, "queryStringParameters": None}
        _assert_500_with_cors(get_breeder_stats(event, None))
