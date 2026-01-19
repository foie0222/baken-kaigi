"""GetConsultationUseCaseのテスト."""
import pytest

from src.domain.entities import CartItem, ConsultationSession
from src.domain.enums import BetType, SessionStatus
from src.domain.identifiers import RaceId, SessionId, UserId
from src.domain.ports import ConsultationSessionRepository
from src.domain.value_objects import (
    AmountFeedback,
    BetSelection,
    DataFeedback,
    HorseDataSummary,
    HorseNumbers,
    Money,
)


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


class TestGetConsultationUseCase:
    """GetConsultationUseCaseの単体テスト."""

    def test_セッションIDでセッション情報を取得できる(self) -> None:
        """セッションIDでセッション情報を取得できることを確認."""
        from src.application.use_cases.get_consultation import GetConsultationUseCase

        session_repo = MockConsultationSessionRepository()

        session = create_started_session()
        session_repo.save(session)

        use_case = GetConsultationUseCase(session_repo)
        result = use_case.execute(session.session_id)

        assert result is not None
        assert result.session_id == session.session_id
        assert result.status == SessionStatus.IN_PROGRESS
        assert result.total_amount.value == 100
        assert len(result.cart_items) == 1

    def test_存在しないセッションIDでNoneを返す(self) -> None:
        """存在しないセッションIDでNoneが返ることを確認."""
        from src.application.use_cases.get_consultation import GetConsultationUseCase

        session_repo = MockConsultationSessionRepository()

        use_case = GetConsultationUseCase(session_repo)
        result = use_case.execute(SessionId("nonexistent"))

        assert result is None

    def test_メッセージ付きのセッションを取得できる(self) -> None:
        """メッセージ付きのセッションを取得できることを確認."""
        from src.application.use_cases.get_consultation import GetConsultationUseCase

        session_repo = MockConsultationSessionRepository()

        session = create_started_session()
        session.add_user_message("質問です")
        session.add_ai_message("回答です")
        session_repo.save(session)

        use_case = GetConsultationUseCase(session_repo)
        result = use_case.execute(session.session_id)

        assert result is not None
        assert len(result.messages) == 2
        assert result.messages[0].content == "質問です"
        assert result.messages[1].content == "回答です"

    def test_フィードバック付きのセッションを取得できる(self) -> None:
        """フィードバック付きのセッションを取得できることを確認."""
        from src.application.use_cases.get_consultation import GetConsultationUseCase

        session_repo = MockConsultationSessionRepository()

        session = create_started_session()
        cart_items = session.get_cart_snapshot()

        # データフィードバックを設定
        horse_summary = HorseDataSummary(
            horse_number=1,
            horse_name="ダノンデサイル",
            recent_results="1-1-2",
            jockey_stats="勝率20%",
            track_suitability="適性あり",
            current_odds="3.5",
            popularity=1,
        )
        data_feedback = DataFeedback.create(
            cart_item_id=cart_items[0].item_id,
            horse_summaries=[horse_summary],
            overall_comment="良い買い目です",
        )
        session.set_data_feedbacks([data_feedback])

        # 掛け金フィードバックを設定
        amount_feedback = AmountFeedback.create(total_amount=Money(100))
        session.set_amount_feedback(amount_feedback)

        session_repo.save(session)

        use_case = GetConsultationUseCase(session_repo)
        result = use_case.execute(session.session_id)

        assert result is not None
        assert len(result.data_feedbacks) == 1
        assert result.amount_feedback is not None

    def test_終了したセッションを取得できる(self) -> None:
        """終了したセッションを取得できることを確認."""
        from src.application.use_cases.get_consultation import GetConsultationUseCase

        session_repo = MockConsultationSessionRepository()

        session = create_started_session()
        session.end()
        session_repo.save(session)

        use_case = GetConsultationUseCase(session_repo)
        result = use_case.execute(session.session_id)

        assert result is not None
        assert result.status == SessionStatus.COMPLETED
