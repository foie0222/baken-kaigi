"""依存性注入コンテナ."""
from src.domain.ports import (
    AIClient,
    CartRepository,
    ConsultationSessionRepository,
    RaceDataProvider,
)
from src.infrastructure.repositories import (
    InMemoryCartRepository,
    InMemoryConsultationSessionRepository,
)


class Dependencies:
    """依存性を管理するコンテナ.

    本番環境では環境変数等で実装を切り替える。
    現在はインメモリ実装を使用。
    """

    _cart_repository: CartRepository | None = None
    _session_repository: ConsultationSessionRepository | None = None
    _race_data_provider: RaceDataProvider | None = None
    _ai_client: AIClient | None = None

    @classmethod
    def get_cart_repository(cls) -> CartRepository:
        """カートリポジトリを取得する."""
        if cls._cart_repository is None:
            cls._cart_repository = InMemoryCartRepository()
        return cls._cart_repository

    @classmethod
    def get_session_repository(cls) -> ConsultationSessionRepository:
        """セッションリポジトリを取得する."""
        if cls._session_repository is None:
            cls._session_repository = InMemoryConsultationSessionRepository()
        return cls._session_repository

    @classmethod
    def get_race_data_provider(cls) -> RaceDataProvider:
        """レースデータプロバイダを取得する."""
        if cls._race_data_provider is None:
            # TODO: 実際の実装に置き換える
            raise NotImplementedError("RaceDataProvider implementation required")
        return cls._race_data_provider

    @classmethod
    def get_ai_client(cls) -> AIClient:
        """AIクライアントを取得する."""
        if cls._ai_client is None:
            # TODO: 実際の実装に置き換える
            raise NotImplementedError("AIClient implementation required")
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
