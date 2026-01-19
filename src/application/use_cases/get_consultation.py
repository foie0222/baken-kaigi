"""相談セッション取得ユースケース."""
from dataclasses import dataclass
from datetime import datetime

from src.domain.entities import CartItem, Message
from src.domain.enums import SessionStatus
from src.domain.identifiers import SessionId
from src.domain.ports import ConsultationSessionRepository
from src.domain.value_objects import AmountFeedback, DataFeedback, Money


@dataclass(frozen=True)
class GetConsultationResult:
    """相談セッション取得結果."""

    session_id: SessionId
    status: SessionStatus
    cart_items: list[CartItem]
    messages: list[Message]
    data_feedbacks: list[DataFeedback]
    amount_feedback: AmountFeedback | None
    total_amount: Money
    started_at: datetime
    ended_at: datetime | None


class GetConsultationUseCase:
    """相談セッションを取得するユースケース."""

    def __init__(self, session_repository: ConsultationSessionRepository) -> None:
        """初期化.

        Args:
            session_repository: セッションリポジトリ
        """
        self._session_repository = session_repository

    def execute(self, session_id: SessionId) -> GetConsultationResult | None:
        """相談セッションを取得する.

        Args:
            session_id: セッションID

        Returns:
            相談セッション取得結果（存在しない場合はNone）
        """
        session = self._session_repository.find_by_id(session_id)
        if session is None:
            return None

        return GetConsultationResult(
            session_id=session.session_id,
            status=session.status,
            cart_items=session.get_cart_snapshot(),
            messages=session.get_messages(),
            data_feedbacks=session.get_data_feedbacks(),
            amount_feedback=session.get_amount_feedback(),
            total_amount=session.get_total_amount(),
            started_at=session.started_at,
            ended_at=session.ended_at,
        )
