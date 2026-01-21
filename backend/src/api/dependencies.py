"""依存性注入コンテナ."""
import os

from src.domain.ports import (
    AIClient,
    CartRepository,
    ConsultationSessionRepository,
    RaceDataProvider,
)
from src.infrastructure import (
    InMemoryCartRepository,
    InMemoryConsultationSessionRepository,
    MockAIClient,
    MockRaceDataProvider,
)


def _use_dynamodb() -> bool:
    """DynamoDBを使用するか判定する."""
    # CART_TABLE_NAME が設定されていればDynamoDBを使用
    return os.environ.get("CART_TABLE_NAME") is not None


def _use_jravan() -> bool:
    """JRA-VAN Data Lab.を使用するか判定する."""
    return os.environ.get("RACE_DATA_PROVIDER") == "jravan"


def _use_claude() -> bool:
    """Claude APIを使用するか判定する."""
    return os.environ.get("ANTHROPIC_API_KEY") is not None


class Dependencies:
    """依存性を管理するコンテナ.

    CART_TABLE_NAME 環境変数が設定されている場合はDynamoDB実装を使用。
    そうでない場合はインメモリ実装を使用（ローカル開発・テスト用）。
    """

    _cart_repository: CartRepository | None = None
    _session_repository: ConsultationSessionRepository | None = None
    _race_data_provider: RaceDataProvider | None = None
    _ai_client: AIClient | None = None

    @classmethod
    def get_cart_repository(cls) -> CartRepository:
        """カートリポジトリを取得する."""
        if cls._cart_repository is None:
            if _use_dynamodb():
                from src.infrastructure import DynamoDBCartRepository

                cls._cart_repository = DynamoDBCartRepository()
            else:
                cls._cart_repository = InMemoryCartRepository()
        return cls._cart_repository

    @classmethod
    def get_session_repository(cls) -> ConsultationSessionRepository:
        """セッションリポジトリを取得する."""
        if cls._session_repository is None:
            if _use_dynamodb():
                from src.infrastructure import DynamoDBConsultationSessionRepository

                cls._session_repository = DynamoDBConsultationSessionRepository()
            else:
                cls._session_repository = InMemoryConsultationSessionRepository()
        return cls._session_repository

    @classmethod
    def get_race_data_provider(cls) -> RaceDataProvider:
        """レースデータプロバイダを取得する."""
        if cls._race_data_provider is None:
            if _use_jravan():
                from src.infrastructure.providers import JraVanRaceDataProvider

                cls._race_data_provider = JraVanRaceDataProvider()
            else:
                cls._race_data_provider = MockRaceDataProvider()
        return cls._race_data_provider

    @classmethod
    def get_ai_client(cls) -> AIClient:
        """AIクライアントを取得する."""
        if cls._ai_client is None:
            if _use_claude():
                from src.infrastructure import ClaudeAIClient

                cls._ai_client = ClaudeAIClient()
            else:
                cls._ai_client = MockAIClient()
        return cls._ai_client

    @classmethod
    def set_cart_repository(cls, repository: CartRepository) -> None:
        """カートリポジトリを設定する（テスト用）."""
        cls._cart_repository = repository

    @classmethod
    def set_session_repository(cls, repository: ConsultationSessionRepository) -> None:
        """セッションリポジトリを設定する（テスト用）."""
        cls._session_repository = repository

    @classmethod
    def set_race_data_provider(cls, provider: RaceDataProvider) -> None:
        """レースデータプロバイダを設定する（テスト用）."""
        cls._race_data_provider = provider

    @classmethod
    def set_ai_client(cls, client: AIClient) -> None:
        """AIクライアントを設定する（テスト用）."""
        cls._ai_client = client

    @classmethod
    def reset(cls) -> None:
        """全ての依存性をリセットする（テスト用）."""
        cls._cart_repository = None
        cls._session_repository = None
        cls._race_data_provider = None
        cls._ai_client = None
