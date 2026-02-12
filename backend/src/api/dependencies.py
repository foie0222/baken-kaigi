"""依存性注入コンテナ."""
import os

from src.domain.ports import (
    AIClient,
    AgentRepository,
    AgentReviewRepository,
    BettingRecordRepository,
    CartRepository,
    ConsultationSessionRepository,
    IpatCredentialsProvider,
    IpatGateway,
    LossLimitChangeRepository,
    PurchaseOrderRepository,
    RaceDataProvider,
    SpendingLimitProvider,
)
from src.domain.ports.user_repository import UserRepository
from src.infrastructure import (
    InMemoryCartRepository,
    InMemoryConsultationSessionRepository,
    InMemoryLossLimitChangeRepository,
    InMemoryUserRepository,
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


class Dependencies:
    """依存性を管理するコンテナ.

    CART_TABLE_NAME 環境変数が設定されている場合はDynamoDB実装を使用。
    そうでない場合はインメモリ実装を使用（ローカル開発・テスト用）。
    """

    _cart_repository: CartRepository | None = None
    _session_repository: ConsultationSessionRepository | None = None
    _race_data_provider: RaceDataProvider | None = None
    _ai_client: AIClient | None = None
    _user_repository: UserRepository | None = None
    _purchase_order_repository: PurchaseOrderRepository | None = None
    _ipat_gateway: IpatGateway | None = None
    _credentials_provider: IpatCredentialsProvider | None = None
    _spending_limit_provider: SpendingLimitProvider | None = None
    _betting_record_repository: BettingRecordRepository | None = None
    _loss_limit_change_repository: LossLimitChangeRepository | None = None
    _agent_repository: AgentRepository | None = None
    _agent_review_repository: AgentReviewRepository | None = None

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
        """AIクライアントを取得する.

        Note: AI相談は AgentCore 経由（/api/consultation）で行う。
        """
        if cls._ai_client is None:
            cls._ai_client = MockAIClient()
        return cls._ai_client

    @classmethod
    def get_user_repository(cls) -> UserRepository:
        """ユーザーリポジトリを取得する."""
        if cls._user_repository is None:
            if _use_dynamodb():
                from src.infrastructure.repositories import DynamoDBUserRepository

                cls._user_repository = DynamoDBUserRepository()
            else:
                cls._user_repository = InMemoryUserRepository()
        return cls._user_repository

    @classmethod
    def set_user_repository(cls, repository: UserRepository) -> None:
        """ユーザーリポジトリを設定する（テスト用）."""
        cls._user_repository = repository

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
    def get_purchase_order_repository(cls) -> PurchaseOrderRepository:
        """購入注文リポジトリを取得する."""
        if cls._purchase_order_repository is None:
            if os.environ.get("PURCHASE_ORDER_TABLE_NAME") is not None:
                from src.infrastructure.repositories.dynamodb_purchase_order_repository import (
                    DynamoDBPurchaseOrderRepository,
                )

                cls._purchase_order_repository = DynamoDBPurchaseOrderRepository()
            else:
                from src.infrastructure.repositories.in_memory_purchase_order_repository import (
                    InMemoryPurchaseOrderRepository,
                )

                cls._purchase_order_repository = InMemoryPurchaseOrderRepository()
        return cls._purchase_order_repository

    @classmethod
    def set_purchase_order_repository(cls, repository: PurchaseOrderRepository) -> None:
        """購入注文リポジトリを設定する（テスト用）."""
        cls._purchase_order_repository = repository

    @classmethod
    def get_ipat_gateway(cls) -> IpatGateway:
        """IPATゲートウェイを取得する."""
        if cls._ipat_gateway is None:
            if os.environ.get("JRAVAN_API_URL") is not None:
                from src.infrastructure.providers.jravan_ipat_gateway import (
                    JraVanIpatGateway,
                )

                cls._ipat_gateway = JraVanIpatGateway()
            else:
                from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway

                cls._ipat_gateway = MockIpatGateway()
        return cls._ipat_gateway

    @classmethod
    def set_ipat_gateway(cls, gateway: IpatGateway) -> None:
        """IPATゲートウェイを設定する（テスト用）."""
        cls._ipat_gateway = gateway

    @classmethod
    def get_credentials_provider(cls) -> IpatCredentialsProvider:
        """IPAT認証情報プロバイダーを取得する."""
        if cls._credentials_provider is None:
            if _use_dynamodb():
                from src.infrastructure.providers.secrets_manager_credentials_provider import (
                    SecretsManagerCredentialsProvider,
                )

                cls._credentials_provider = SecretsManagerCredentialsProvider()
            else:
                from src.infrastructure.providers.in_memory_credentials_provider import (
                    InMemoryCredentialsProvider,
                )

                cls._credentials_provider = InMemoryCredentialsProvider()
        return cls._credentials_provider

    @classmethod
    def set_credentials_provider(cls, provider: IpatCredentialsProvider) -> None:
        """IPAT認証情報プロバイダーを設定する（テスト用）."""
        cls._credentials_provider = provider

    @classmethod
    def get_loss_limit_change_repository(cls) -> LossLimitChangeRepository:
        """負け額限度額変更リポジトリを取得する."""
        if cls._loss_limit_change_repository is None:
            if _use_dynamodb():
                from src.infrastructure.repositories.dynamodb_loss_limit_change_repository import (
                    DynamoDBLossLimitChangeRepository,
                )

                cls._loss_limit_change_repository = DynamoDBLossLimitChangeRepository()
            else:
                cls._loss_limit_change_repository = InMemoryLossLimitChangeRepository()
        return cls._loss_limit_change_repository

    @classmethod
    def set_loss_limit_change_repository(cls, repository: LossLimitChangeRepository) -> None:
        """負け額限度額変更リポジトリを設定する（テスト用）."""
        cls._loss_limit_change_repository = repository

    @classmethod
    def get_spending_limit_provider(cls) -> SpendingLimitProvider:
        """月間支出制限プロバイダーを取得する."""
        if cls._spending_limit_provider is None:
            from src.infrastructure.providers.stub_spending_limit_provider import (
                StubSpendingLimitProvider,
            )

            cls._spending_limit_provider = StubSpendingLimitProvider()
        return cls._spending_limit_provider

    @classmethod
    def set_spending_limit_provider(cls, provider: SpendingLimitProvider) -> None:
        """月間支出制限プロバイダーを設定する（テスト用）."""
        cls._spending_limit_provider = provider

    @classmethod
    def get_betting_record_repository(cls) -> BettingRecordRepository:
        """投票記録リポジトリを取得する."""
        if cls._betting_record_repository is None:
            if os.environ.get("BETTING_RECORD_TABLE_NAME") is not None:
                from src.infrastructure.repositories.dynamodb_betting_record_repository import (
                    DynamoDBBettingRecordRepository,
                )

                cls._betting_record_repository = DynamoDBBettingRecordRepository()
            else:
                from src.infrastructure.repositories.in_memory_betting_record_repository import (
                    InMemoryBettingRecordRepository,
                )

                cls._betting_record_repository = InMemoryBettingRecordRepository()
        return cls._betting_record_repository

    @classmethod
    def set_betting_record_repository(cls, repository: BettingRecordRepository) -> None:
        """投票記録リポジトリを設定する（テスト用）."""
        cls._betting_record_repository = repository

    @classmethod
    def get_agent_repository(cls) -> AgentRepository:
        """エージェントリポジトリを取得する."""
        if cls._agent_repository is None:
            if os.environ.get("AGENT_TABLE_NAME") is not None:
                from src.infrastructure.repositories.dynamodb_agent_repository import (
                    DynamoDBAgentRepository,
                )

                cls._agent_repository = DynamoDBAgentRepository()
            else:
                from src.infrastructure.repositories.in_memory_agent_repository import (
                    InMemoryAgentRepository,
                )

                cls._agent_repository = InMemoryAgentRepository()
        return cls._agent_repository

    @classmethod
    def set_agent_repository(cls, repository: AgentRepository) -> None:
        """エージェントリポジトリを設定する（テスト用）."""
        cls._agent_repository = repository

    @classmethod
    def get_agent_review_repository(cls) -> AgentReviewRepository:
        """エージェント振り返りリポジトリを取得する."""
        if cls._agent_review_repository is None:
            if os.environ.get("AGENT_REVIEW_TABLE_NAME") is not None:
                from src.infrastructure.repositories.dynamodb_agent_review_repository import (
                    DynamoDBAgentReviewRepository,
                )

                cls._agent_review_repository = DynamoDBAgentReviewRepository()
            else:
                from src.infrastructure.repositories.in_memory_agent_review_repository import (
                    InMemoryAgentReviewRepository,
                )

                cls._agent_review_repository = InMemoryAgentReviewRepository()
        return cls._agent_review_repository

    @classmethod
    def set_agent_review_repository(cls, repository: AgentReviewRepository) -> None:
        """エージェント振り返りリポジトリを設定する（テスト用）."""
        cls._agent_review_repository = repository

    @classmethod
    def reset(cls) -> None:
        """全ての依存性をリセットする（テスト用）."""
        cls._cart_repository = None
        cls._session_repository = None
        cls._race_data_provider = None
        cls._ai_client = None
        cls._user_repository = None
        cls._purchase_order_repository = None
        cls._ipat_gateway = None
        cls._credentials_provider = None
        cls._spending_limit_provider = None
        cls._betting_record_repository = None
        cls._loss_limit_change_repository = None
        cls._agent_repository = None
        cls._agent_review_repository = None
