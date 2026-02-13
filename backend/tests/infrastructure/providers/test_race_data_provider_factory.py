"""RaceDataProvider ファクトリのテスト."""
from unittest.mock import patch

import pytest


class TestCreateRaceDataProvider:

    def test_環境変数dynamodbでDynamoDbProviderを返す(self):
        with patch.dict("os.environ", {"RACE_DATA_PROVIDER": "dynamodb"}):
            with patch("boto3.resource"):
                from src.infrastructure.providers.race_data_provider_factory import (
                    create_race_data_provider,
                )
                from src.infrastructure.providers.dynamodb_race_data_provider import (
                    DynamoDbRaceDataProvider,
                )

                provider = create_race_data_provider()
                assert isinstance(provider, DynamoDbRaceDataProvider)

    def test_環境変数jravanでJraVanProviderを返す(self):
        with patch.dict("os.environ", {"RACE_DATA_PROVIDER": "jravan"}):
            from src.infrastructure.providers.race_data_provider_factory import (
                create_race_data_provider,
            )
            from src.infrastructure.providers.jravan_race_data_provider import (
                JraVanRaceDataProvider,
            )

            provider = create_race_data_provider()
            assert isinstance(provider, JraVanRaceDataProvider)

    def test_環境変数未設定でMockProviderを返す(self):
        with patch.dict("os.environ", {}, clear=True):
            from src.infrastructure.providers.race_data_provider_factory import (
                create_race_data_provider,
            )
            from src.infrastructure import MockRaceDataProvider

            provider = create_race_data_provider()
            assert isinstance(provider, MockRaceDataProvider)
