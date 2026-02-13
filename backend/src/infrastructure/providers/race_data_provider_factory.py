"""RaceDataProvider ファクトリ."""
import os

from src.domain.ports.race_data_provider import RaceDataProvider


def create_race_data_provider() -> RaceDataProvider:
    """環境変数に基づいてRaceDataProviderを生成する.

    RACE_DATA_PROVIDER:
        "dynamodb" → DynamoDbRaceDataProvider
        "jravan"   → JraVanRaceDataProvider
        未設定      → MockRaceDataProvider
    """
    provider_type = os.environ.get("RACE_DATA_PROVIDER", "")
    if provider_type == "dynamodb":
        from src.infrastructure.providers.dynamodb_race_data_provider import (
            DynamoDbRaceDataProvider,
        )

        return DynamoDbRaceDataProvider()
    elif provider_type == "jravan":
        from src.infrastructure.providers.jravan_race_data_provider import (
            JraVanRaceDataProvider,
        )

        return JraVanRaceDataProvider()
    else:
        from src.infrastructure.providers.mock_race_data_provider import (
            MockRaceDataProvider,
        )

        return MockRaceDataProvider()
