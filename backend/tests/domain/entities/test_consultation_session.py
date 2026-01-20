"""ConsultationSessionのテスト."""
import pytest

from src.domain.value_objects import AmountFeedback
from src.domain.value_objects import BetSelection
from src.domain.enums import BetType
from src.domain.entities import CartItem
from src.domain.entities import ConsultationSession
from src.domain.value_objects import DataFeedback
from src.domain.value_objects import HorseDataSummary
from src.domain.value_objects import HorseNumbers
from src.domain.identifiers import ItemId
from src.domain.value_objects import Money
from src.domain.identifiers import RaceId
from src.domain.enums import SessionStatus
from src.domain.identifiers import UserId


def create_test_cart_item() -> CartItem:
    """テスト用のCartItemを作成する."""
    bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
    return CartItem.create(RaceId("race-1"), "テストレース", bet)


def create_test_data_feedback(item_id: ItemId) -> DataFeedback:
    """テスト用のDataFeedbackを作成する."""
    summary = HorseDataSummary(
        horse_number=1,
        horse_name="テスト馬",
        recent_results="1-1-1",
        jockey_stats="勝率30%",
        track_suitability="良馬場得意",
        current_odds="3.0",
        popularity=1,
    )
    return DataFeedback.create(
        cart_item_id=item_id,
        horse_summaries=[summary],
        overall_comment="良い買い目です",
    )


class TestConsultationSession:
    """ConsultationSessionの単体テスト."""

    def test_createで未開始状態のセッションを生成(self) -> None:
        """createメソッドでNOT_STARTED状態のセッションを生成できることを確認."""
        session = ConsultationSession.create()
        assert session.status == SessionStatus.NOT_STARTED

    def test_createでユーザー紐付きセッションを生成(self) -> None:
        """createメソッドでユーザー紐付きセッションを生成できることを確認."""
        session = ConsultationSession.create(user_id=UserId("user-1"))
        assert session.user_id.value == "user-1"

    def test_startでセッションを開始(self) -> None:
        """startメソッドでセッションを開始できることを確認."""
        session = ConsultationSession.create()
        items = [create_test_cart_item()]
        session.start(items)
        assert session.status == SessionStatus.IN_PROGRESS
        assert len(session.get_cart_snapshot()) == 1

    def test_startで空のカートはエラー(self) -> None:
        """startで空のカートアイテムリストを渡すとエラーになることを確認."""
        session = ConsultationSession.create()
        with pytest.raises(ValueError, match="empty cart"):
            session.start([])

    def test_startで既に開始済みの場合エラー(self) -> None:
        """startで既に開始済みのセッションに対してエラーになることを確認."""
        session = ConsultationSession.create()
        items = [create_test_cart_item()]
        session.start(items)
        with pytest.raises(ValueError, match="NOT_STARTED"):
            session.start(items)

    def test_add_user_messageでユーザーメッセージを追加(self) -> None:
        """add_user_messageでユーザーメッセージを追加できることを確認."""
        session = ConsultationSession.create()
        session.start([create_test_cart_item()])
        msg = session.add_user_message("質問です")
        assert msg.content == "質問です"
        assert len(session.get_messages()) == 1

    def test_add_ai_messageでAIメッセージを追加(self) -> None:
        """add_ai_messageでAIメッセージを追加できることを確認."""
        session = ConsultationSession.create()
        session.start([create_test_cart_item()])
        msg = session.add_ai_message("回答です")
        assert msg.content == "回答です"
        assert msg.is_from_ai() is True

    def test_add_system_messageでシステムメッセージを追加(self) -> None:
        """add_system_messageでシステムメッセージを追加できることを確認."""
        session = ConsultationSession.create()
        session.start([create_test_cart_item()])
        msg = session.add_system_message("通知です")
        assert msg.is_system() is True

    def test_未開始状態でメッセージ追加はエラー(self) -> None:
        """未開始状態でメッセージを追加しようとするとエラーになることを確認."""
        session = ConsultationSession.create()
        with pytest.raises(ValueError, match="IN_PROGRESS"):
            session.add_user_message("テスト")

    def test_set_data_feedbacksでフィードバックを設定(self) -> None:
        """set_data_feedbacksでデータフィードバックを設定できることを確認."""
        session = ConsultationSession.create()
        item = create_test_cart_item()
        session.start([item])
        feedback = create_test_data_feedback(item.item_id)
        session.set_data_feedbacks([feedback])
        assert len(session.get_data_feedbacks()) == 1

    def test_set_amount_feedbackでフィードバックを設定(self) -> None:
        """set_amount_feedbackで掛け金フィードバックを設定できることを確認."""
        session = ConsultationSession.create()
        session.start([create_test_cart_item()])
        feedback = AmountFeedback.create(total_amount=Money(1000))
        session.set_amount_feedback(feedback)
        assert session.get_amount_feedback() is not None

    def test_endでセッションを終了(self) -> None:
        """endメソッドでセッションを終了できることを確認."""
        session = ConsultationSession.create()
        session.start([create_test_cart_item()])
        session.end()
        assert session.status == SessionStatus.COMPLETED
        assert session.ended_at is not None

    def test_終了後にメッセージ追加はエラー(self) -> None:
        """終了後にメッセージを追加しようとするとエラーになることを確認."""
        session = ConsultationSession.create()
        session.start([create_test_cart_item()])
        session.end()
        with pytest.raises(ValueError, match="IN_PROGRESS"):
            session.add_user_message("テスト")

    def test_get_total_amountで合計掛け金を取得(self) -> None:
        """get_total_amountで合計掛け金を取得できることを確認."""
        session = ConsultationSession.create()
        bet1 = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(1000))
        bet2 = BetSelection(BetType.PLACE, HorseNumbers.of(2), Money(500))
        item1 = CartItem.create(RaceId("r1"), "R1", bet1)
        item2 = CartItem.create(RaceId("r2"), "R2", bet2)
        session.start([item1, item2])
        assert session.get_total_amount().value == 1500

    def test_is_limit_exceededで限度額超過を判定(self) -> None:
        """is_limit_exceededで限度額超過を判定できることを確認."""
        session = ConsultationSession.create()
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(1000))
        item = CartItem.create(RaceId("r1"), "R1", bet)
        session.start([item])
        assert session.is_limit_exceeded(Money(500)) is True
        assert session.is_limit_exceeded(Money(2000)) is False

    def test_get_cart_snapshotで防御的コピーを取得(self) -> None:
        """get_cart_snapshotで防御的コピーが返ることを確認."""
        session = ConsultationSession.create()
        session.start([create_test_cart_item()])
        snapshot = session.get_cart_snapshot()
        snapshot.clear()
        assert len(session.get_cart_snapshot()) == 1

    def test_get_messagesで防御的コピーを取得(self) -> None:
        """get_messagesで防御的コピーが返ることを確認."""
        session = ConsultationSession.create()
        session.start([create_test_cart_item()])
        session.add_user_message("テスト")
        messages = session.get_messages()
        messages.clear()
        assert len(session.get_messages()) == 1
