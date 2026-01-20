"""AI相談開始ユースケース."""
from dataclasses import dataclass

from src.domain.entities import CartItem, ConsultationSession
from src.domain.enums import SessionStatus
from src.domain.identifiers import CartId, SessionId
from src.domain.ports import (
    AIClient,
    CartRepository,
    ConsultationSessionRepository,
    RaceDataProvider,
)
from src.domain.services import FeedbackGenerator
from src.domain.value_objects import AmountFeedback, DataFeedback, Money


class CartNotFoundError(Exception):
    """カートが見つからないエラー."""

    def __init__(self, cart_id: CartId) -> None:
        self.cart_id = cart_id
        super().__init__(f"Cart not found: {cart_id}")


class EmptyCartError(Exception):
    """空のカートエラー."""

    def __init__(self, cart_id: CartId) -> None:
        self.cart_id = cart_id
        super().__init__(f"Cart is empty: {cart_id}")


@dataclass(frozen=True)
class StartConsultationResult:
    """相談開始結果."""

    session_id: SessionId
    status: SessionStatus
    cart_items: list[CartItem]
    total_amount: Money
    data_feedbacks: list[DataFeedback]
    amount_feedback: AmountFeedback | None


class StartConsultationUseCase:
    """AI相談を開始するユースケース."""

    def __init__(
        self,
        cart_repository: CartRepository,
        session_repository: ConsultationSessionRepository,
        race_data_provider: RaceDataProvider,
        ai_client: AIClient,
    ) -> None:
        """初期化.

        Args:
            cart_repository: カートリポジトリ
            session_repository: セッションリポジトリ
            race_data_provider: レースデータプロバイダ
            ai_client: AIクライアント
        """
        self._cart_repository = cart_repository
        self._session_repository = session_repository
        self._feedback_generator = FeedbackGenerator(ai_client, race_data_provider)

    def execute(
        self,
        cart_id: CartId,
        remaining_loss_limit: Money | None = None,
        average_amount: Money | None = None,
    ) -> StartConsultationResult:
        """相談セッションを開始する.

        Args:
            cart_id: カートID
            remaining_loss_limit: 残り許容負け額（ログインユーザーのみ）
            average_amount: 過去の平均掛け金（ログインユーザーのみ）

        Returns:
            相談開始結果

        Raises:
            CartNotFoundError: カートが見つからない場合
            EmptyCartError: カートが空の場合
        """
        # カートを取得
        cart = self._cart_repository.find_by_id(cart_id)
        if cart is None:
            raise CartNotFoundError(cart_id)

        if cart.is_empty():
            raise EmptyCartError(cart_id)

        cart_items = cart.get_items()

        # セッションを作成・開始
        session = ConsultationSession.create(user_id=cart.user_id)
        session.start(cart_items)

        # フィードバックを生成
        data_feedbacks = self._feedback_generator.generate_data_feedbacks(cart_items)
        amount_feedback = self._feedback_generator.generate_amount_feedback(
            total_amount=cart.get_total_amount(),
            remaining_loss_limit=remaining_loss_limit,
            average_amount=average_amount,
        )

        # セッションにフィードバックを設定
        session.set_data_feedbacks(data_feedbacks)
        session.set_amount_feedback(amount_feedback)

        # セッションを保存
        self._session_repository.save(session)

        return StartConsultationResult(
            session_id=session.session_id,
            status=session.status,
            cart_items=cart_items,
            total_amount=cart.get_total_amount(),
            data_feedbacks=data_feedbacks,
            amount_feedback=amount_feedback,
        )
