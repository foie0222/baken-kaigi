"""RaceDataProvider ファクトリ."""
import os

from src.domain.ports.race_data_provider import RaceDataProvider


def create_race_data_provider() -> RaceDataProvider:
    """環境変数に基づいてRaceDataProviderを生成する.

    RACE_DATA_PROVIDER:
        "mock"  → MockRaceDataProvider（ローカル開発・テスト用）
        未設定   → DynamoDbRaceDataProvider（デフォルト）
    """
    provider_type = os.environ.get("RACE_DATA_PROVIDER", "")
    if provider_type == "mock":
        from src.infrastructure.providers.mock_race_data_provider import (
            MockRaceDataProvider,
        )

        return MockRaceDataProvider()
    else:
        from src.infrastructure.providers.dynamodb_race_data_provider import (
            DynamoDbRaceDataProvider,
        )

        return DynamoDbRaceDataProvider()
