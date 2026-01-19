"""SendMessageUseCaseのテスト."""
from datetime import datetime

import pytest

from src.domain.entities import CartItem, ConsultationSession, Message
from src.domain.enums import BetType, SessionStatus
from src.domain.identifiers import RaceId, SessionId, UserId
from src.domain.ports import (
    AIClient,
    AmountFeedbackContext,
    BetFeedbackContext,
    ConsultationContext,
    ConsultationSessionRepository,
)
from src.domain.value_objects import BetSelection, HorseNumbers, Money


class MockConsultationSessionRepository(ConsultationSessionRepository):
    """テスト用のモックセッションリポジトリ."""

    def __init__(self) -> None:
        self._sessions: dict[str, ConsultationSession] = {}

    def save(self, session: ConsultationSession) -> None:
        self._sessions[str(session.session_id)] = session

    def find_by_id(self, session_id: SessionId) -> ConsultationSession | None:
        return self._sessions.get(str(session_id))

    def find_by_user_id(self, user_id: UserId) -> list[ConsultationSession]:
        return [s for s in self._sessions.values() if s.user_id == user_id]

    def delete(self, session_id: SessionId) -> None:
        if str(session_id) in self._sessions:
            del self._sessions[str(session_id)]


class MockAIClient(AIClient):
    """テスト用のモックAIクライアント."""

    def generate_bet_feedback(self, context: BetFeedbackContext) -> str:
        return "フィードバック"

    def generate_amount_feedback(self, context: AmountFeedbackContext) -> str:
        return "掛け金フィードバック"

    def generate_conversation_response(
        self, messages: list[Message], context: ConsultationContext
    ) -> str:
        return "AIの応答です。立ち止まって考えましょう。"


def create_started_session() -> ConsultationSession:
    """テスト用の開始済みセッションを作成."""
    session = ConsultationSession.create()
    cart_item = CartItem.create(
        race_id=RaceId("2024060111"),
        race_name="日本ダービー",
        bet_selection=BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers([1]),
            amount=Money(100),
        ),
    )
    session.start([cart_item])
    return session


class TestSendMessageUseCase:
    """SendMessageUseCaseの単体テスト."""

    def test_メッセージを送信してAI応答を取得できる(self) -> None:
        """メッセージを送信してAI応答を取得できることを確認."""
        from src.application.use_cases.send_message import SendMessageUseCase

        session_repo = MockConsultationSessionRepository()
        ai_client = MockAIClient()

        session = create_started_session()
        session_repo.save(session)

        use_case = SendMessageUseCase(session_repo, ai_client)
        result = use_case.execute(session.session_id, "この買い目で大丈夫ですか？")

        assert result.user_message.content == "この買い目で大丈夫ですか？"
        assert result.ai_message.content == "AIの応答です。立ち止まって考えましょう。"
        assert len(result.messages) == 2

    def test_存在しないセッションIDでエラー(self) -> None:
        """存在しないセッションIDでエラーが発生することを確認."""
        from src.application.use_cases.send_message import (
            SendMessageUseCase,
            SessionNotFoundError,
        )

        session_repo = MockConsultationSessionRepository()
        ai_client = MockAIClient()

        use_case = SendMessageUseCase(session_repo, ai_client)

        with pytest.raises(SessionNotFoundError):
            use_case.execute(SessionId("nonexistent"), "メッセージ")

    def test_終了したセッションではエラー(self) -> None:
        """終了したセッションでエラーが発生することを確認."""
        from src.application.use_cases.send_message import (
            SendMessageUseCase,
            SessionNotInProgressError,
        )

        session_repo = MockConsultationSessionRepository()
        ai_client = MockAIClient()

        session = create_started_session()
        session.end()
        session_repo.save(session)

        use_case = SendMessageUseCase(session_repo, ai_client)

        with pytest.raises(SessionNotInProgressError):
            use_case.execute(session.session_id, "メッセージ")

    def test_連続してメッセージを送信できる(self) -> None:
        """連続してメッセージを送信できることを確認."""
        from src.application.use_cases.send_message import SendMessageUseCase

        session_repo = MockConsultationSessionRepository()
        ai_client = MockAIClient()

        session = create_started_session()
        session_repo.save(session)

        use_case = SendMessageUseCase(session_repo, ai_client)

        # 1回目
        result1 = use_case.execute(session.session_id, "1回目のメッセージ")
        assert len(result1.messages) == 2

        # 2回目
        result2 = use_case.execute(session.session_id, "2回目のメッセージ")
        assert len(result2.messages) == 4
