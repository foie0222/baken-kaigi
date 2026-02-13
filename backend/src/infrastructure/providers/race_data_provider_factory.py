"""RaceDataProvider ファクトリ."""
import logging
import os

from src.domain.ports.race_data_provider import RaceDataProvider

logger = logging.getLogger(__name__)


def create_race_data_provider() -> RaceDataProvider:
    """環境変数に基づいてRaceDataProviderを生成する.

    RACE_DATA_PROVIDER:
        "mock"     → MockRaceDataProvider（ローカル開発・テスト用）
        "dynamodb" → DynamoDbRaceDataProvider
        未設定      → DynamoDbRaceDataProvider（デフォルト）
    """
    provider_type = os.environ.get("RACE_DATA_PROVIDER")
    if provider_type == "mock":
        from src.infrastructure.providers.mock_race_data_provider import (
            MockRaceDataProvider,
        )

        return MockRaceDataProvider()

    if provider_type and provider_type != "dynamodb":
        logger.warning("Unknown RACE_DATA_PROVIDER=%s, falling back to DynamoDB", provider_type)

    from src.infrastructure.providers.dynamodb_race_data_provider import (
        DynamoDbRaceDataProvider,
    )

    return DynamoDbRaceDataProvider()
