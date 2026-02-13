"""RaceDataProvider ファクトリのテスト."""
from unittest.mock import patch


class TestCreateRaceDataProvider:

    def test_環境変数未設定でDynamoDbProviderを返す(self):
        """デフォルトはDynamoDbRaceDataProvider."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("boto3.resource"):
                from src.infrastructure.providers.race_data_provider_factory import (
                    create_race_data_provider,
                )
                from src.infrastructure.providers.dynamodb_race_data_provider import (
                    DynamoDbRaceDataProvider,
                )

                provider = create_race_data_provider()
                assert isinstance(provider, DynamoDbRaceDataProvider)

    def test_環境変数mockでMockProviderを返す(self):
        with patch.dict("os.environ", {"RACE_DATA_PROVIDER": "mock"}):
            from src.infrastructure.providers.race_data_provider_factory import (
                create_race_data_provider,
            )
            from src.infrastructure import MockRaceDataProvider

            provider = create_race_data_provider()
            assert isinstance(provider, MockRaceDataProvider)
