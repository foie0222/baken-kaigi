"""ConsultationServiceの単体テスト."""
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from src.domain.entities import Cart, ConsultationSession
from src.domain.enums import BetType, SessionStatus
from src.domain.identifiers import ItemId, RaceId, UserId
from src.domain.ports import AIClient, ConsultationContext
from src.domain.services import DeadlineChecker, FeedbackGenerator
from src.domain.services.consultation_service import (
    CartEmptyError,
    ConsultationService,
    DeadlinePassedError,
    SessionNotInProgressError,
)
from src.domain.services.deadline_checker import DeadlineCheckResult
from src.domain.value_objects import (
    AmountFeedback,
    BetSelection,
    DataFeedback,
    HorseDataSummary,
    HorseNumbers,
    Money,
    RaceReference,
)


@pytest.fixture
def mock_ai_client() -> Mock:
    """AIClientのモックを作成."""
    client = Mock(spec=AIClient)
    client.generate_conversation_response.return_value = "AIの応答です"
    return client


@pytest.fixture
def mock_feedback_generator() -> Mock:
    """FeedbackGeneratorのモックを作成."""
    generator = Mock(spec=FeedbackGenerator)
    generator.generate_data_feedbacks.return_value = []
    generator.generate_amount_feedback.return_value = AmountFeedback.create(
        total_amount=Money(1000),
        remaining_loss_limit=None,
    )
    return generator


@pytest.fixture
def mock_deadline_checker() -> Mock:
    """DeadlineCheckerのモックを作成."""
    checker = Mock(spec=DeadlineChecker)
    checker.check_deadlines.return_value = DeadlineCheckResult(
        all_valid=True,
        expired_items=[],
        nearest_deadline=datetime.now() + timedelta(hours=1),
    )
    return checker


@pytest.fixture
def consultation_service(
    mock_feedback_generator: Mock,
    mock_deadline_checker: Mock,
    mock_ai_client: Mock,
) -> ConsultationService:
    """ConsultationServiceインスタンスを作成."""
    return ConsultationService(
        feedback_generator=mock_feedback_generator,
        deadline_checker=mock_deadline_checker,
        ai_client=mock_ai_client,
    )


@pytest.fixture
def cart_with_items() -> Cart:
    """アイテムを含むカートを作成."""
    cart = Cart.create(user_id=UserId("user-1"))
    cart.add_item(
        race_id=RaceId("race-1"),
        race_name="第1レース",
        bet_selection=BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100)),
    )
    return cart


@pytest.fixture
def race_references() -> dict:
    """レース参照の辞書を作成."""
    future_deadline = datetime.now() + timedelta(hours=1)
    return {
        ItemId("item-1"): RaceReference(
            race_id=RaceId("race-1"),
            race_name="第1レース",
            race_number=1,
            venue="東京",
            start_time=future_deadline + timedelta(minutes=10),
            betting_deadline=future_deadline,
        )
    }


class TestConsultationServiceInit:
    """ConsultationService初期化のテスト."""

    def test_依存関係を注入して初期化できる(
        self,
        mock_feedback_generator: Mock,
        mock_deadline_checker: Mock,
        mock_ai_client: Mock,
    ) -> None:
        """依存関係を注入して初期化できることを確認."""
        service = ConsultationService(
            feedback_generator=mock_feedback_generator,
            deadline_checker=mock_deadline_checker,
            ai_client=mock_ai_client,
        )
        assert service._feedback_generator == mock_feedback_generator
        assert service._deadline_checker == mock_deadline_checker
        assert service._ai_client == mock_ai_client


class TestStartConsultation:
    """start_consultationメソッドのテスト."""

    def test_正常にセッションを開始できる(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
    ) -> None:
        """正常にセッションを開始できることを確認."""
        session = consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
        )
        assert session.status == SessionStatus.IN_PROGRESS
        assert len(session.get_cart_snapshot()) > 0

    def test_カートが空の場合CartEmptyErrorを発生(
        self,
        consultation_service: ConsultationService,
        race_references: dict,
    ) -> None:
        """カートが空の場合CartEmptyErrorが発生することを確認."""
        empty_cart = Cart.create()
        with pytest.raises(CartEmptyError, match="カートが空です"):
            consultation_service.start_consultation(
                cart=empty_cart,
                race_references=race_references,
            )

    def test_締め切りが過ぎている場合DeadlinePassedErrorを発生(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
        mock_deadline_checker: Mock,
    ) -> None:
        """締め切りが過ぎている場合DeadlinePassedErrorが発生することを確認."""
        expired_item = ItemId("item-1")
        mock_deadline_checker.check_deadlines.return_value = DeadlineCheckResult(
            all_valid=False,
            expired_items=[expired_item],
            nearest_deadline=None,
        )
        with pytest.raises(DeadlinePassedError) as exc_info:
            consultation_service.start_consultation(
                cart=cart_with_items,
                race_references=race_references,
            )
        assert expired_item in exc_info.value.expired_items

    def test_ユーザーIDを指定してセッションを開始できる(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
    ) -> None:
        """ユーザーIDを指定してセッションを開始できることを確認."""
        user_id = UserId("user-123")
        session = consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
            user_id=user_id,
        )
        assert session.user_id == user_id

    def test_残り損失限度を指定してセッションを開始できる(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
        mock_feedback_generator: Mock,
    ) -> None:
        """残り損失限度を指定してセッションを開始できることを確認."""
        remaining_limit = Money(5000)
        consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
            remaining_loss_limit=remaining_limit,
        )
        mock_feedback_generator.generate_amount_feedback.assert_called_once()
        call_kwargs = mock_feedback_generator.generate_amount_feedback.call_args.kwargs
        assert call_kwargs["remaining_loss_limit"] == remaining_limit


class TestContinueConversation:
    """continue_conversationメソッドのテスト."""

    def test_正常に会話を継続できる(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
    ) -> None:
        """正常に会話を継続できることを確認."""
        session = consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
        )
        updated_session = consultation_service.continue_conversation(
            session=session,
            user_message="この馬はどうですか？",
        )
        messages = updated_session.get_messages()
        assert len(messages) == 2  # ユーザーメッセージ + AI応答
        assert messages[0].content == "この馬はどうですか？"
        assert messages[1].content == "AIの応答です"

    def test_セッションがIN_PROGRESSでない場合SessionNotInProgressErrorを発生(
        self,
        consultation_service: ConsultationService,
    ) -> None:
        """セッションがIN_PROGRESSでない場合SessionNotInProgressErrorが発生することを確認."""
        session = ConsultationSession.create()  # NOT_STARTED状態
        with pytest.raises(SessionNotInProgressError, match="セッションが進行中ではありません"):
            consultation_service.continue_conversation(
                session=session,
                user_message="テスト",
            )

    def test_AIクライアントに正しいコンテキストが渡される(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
        mock_ai_client: Mock,
    ) -> None:
        """AIクライアントに正しいコンテキストが渡されることを確認."""
        session = consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
        )
        consultation_service.continue_conversation(
            session=session,
            user_message="質問です",
        )
        mock_ai_client.generate_conversation_response.assert_called_once()
        call_args = mock_ai_client.generate_conversation_response.call_args
        context = call_args[0][1]
        assert isinstance(context, ConsultationContext)


class TestEndConsultation:
    """end_consultationメソッドのテスト."""

    def test_正常にセッションを終了できる(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
    ) -> None:
        """正常にセッションを終了できることを確認."""
        session = consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
        )
        ended_session = consultation_service.end_consultation(session)
        assert ended_session.status == SessionStatus.COMPLETED


class TestSummarizeCart:
    """_summarize_cartメソッドのテスト."""

    def test_カートが空の場合空メッセージを返す(
        self,
        consultation_service: ConsultationService,
    ) -> None:
        """カートが空の場合、空メッセージを返すことを確認."""
        session = ConsultationSession.create()
        # start()を呼ばずに空のスナップショットを持つセッションを使う
        result = consultation_service._summarize_cart(session)
        assert result == "カートは空です"

    def test_カートにアイテムがある場合要約を返す(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
    ) -> None:
        """カートにアイテムがある場合、要約を返すことを確認."""
        session = consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
        )
        result = consultation_service._summarize_cart(session)
        assert "第1レース" in result
        assert "単勝" in result


class TestSummarizeDataFeedbacks:
    """_summarize_data_feedbacksメソッドのテスト."""

    def test_フィードバックがない場合メッセージを返す(
        self,
        consultation_service: ConsultationService,
    ) -> None:
        """フィードバックがない場合、メッセージを返すことを確認."""
        session = ConsultationSession.create()
        result = consultation_service._summarize_data_feedbacks(session)
        assert result == "フィードバックなし"

    def test_フィードバックがある場合コメントを結合して返す(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
        mock_feedback_generator: Mock,
    ) -> None:
        """フィードバックがある場合、コメントを結合して返すことを確認."""
        feedback = DataFeedback.create(
            cart_item_id=ItemId("item-1"),
            horse_summaries=[
                HorseDataSummary(
                    horse_number=1,
                    horse_name="テスト馬",
                    recent_results="1-2-3",
                    jockey_stats="勝率10%",
                    track_suitability="○",
                    current_odds="3.5",
                    popularity=1,
                    pedigree=None,
                    weight_trend=None,
                    weight_current=None,
                )
            ],
            overall_comment="この馬は好調です",
        )
        mock_feedback_generator.generate_data_feedbacks.return_value = [feedback]

        session = consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
        )
        result = consultation_service._summarize_data_feedbacks(session)
        assert "この馬は好調です" in result


class TestSummarizeAmountFeedback:
    """_summarize_amount_feedbackメソッドのテスト."""

    def test_フィードバックがない場合メッセージを返す(
        self,
        consultation_service: ConsultationService,
    ) -> None:
        """フィードバックがない場合、メッセージを返すことを確認."""
        session = ConsultationSession.create()
        result = consultation_service._summarize_amount_feedback(session)
        assert result == "フィードバックなし"

    def test_フィードバックがある場合コメントを返す(
        self,
        consultation_service: ConsultationService,
        cart_with_items: Cart,
        race_references: dict,
    ) -> None:
        """フィードバックがある場合、コメントを返すことを確認."""
        session = consultation_service.start_consultation(
            cart=cart_with_items,
            race_references=race_references,
        )
        result = consultation_service._summarize_amount_feedback(session)
        # AmountFeedbackのコメントが返される
        assert result != "フィードバックなし"


class TestDeadlinePassedError:
    """DeadlinePassedErrorのテスト."""

    def test_expired_itemsを保持する(self) -> None:
        """expired_itemsを保持することを確認."""
        expired_items = [ItemId("item-1"), ItemId("item-2")]
        error = DeadlinePassedError("締め切りエラー", expired_items)
        assert error.expired_items == expired_items
        assert str(error) == "締め切りエラー"
