"""相談サービス."""
from datetime import datetime

from ..entities import Cart, ConsultationSession
from ..identifiers import UserId
from ..ports import AIClient, ConsultationContext
from ..value_objects import Money, RaceReference

from .deadline_checker import DeadlineChecker
from .feedback_generator import FeedbackGenerator


class CartEmptyError(Exception):
    """カートが空の場合のエラー."""

    pass


class DeadlinePassedError(Exception):
    """締め切りが過ぎている場合のエラー."""

    def __init__(self, message: str, expired_items: list) -> None:
        """初期化."""
        super().__init__(message)
        self.expired_items = expired_items


class SessionNotInProgressError(Exception):
    """セッションが進行中でない場合のエラー."""

    pass


class ConsultationService:
    """カートの買い目に対するAI相談セッションを管理するサービス."""

    def __init__(
        self,
        feedback_generator: FeedbackGenerator,
        deadline_checker: DeadlineChecker,
        ai_client: AIClient,
    ) -> None:
        """初期化."""
        self._feedback_generator = feedback_generator
        self._deadline_checker = deadline_checker
        self._ai_client = ai_client

    def start_consultation(
        self,
        cart: Cart,
        race_references: dict,
        remaining_loss_limit: Money | None = None,
        user_id: UserId | None = None,
    ) -> ConsultationSession:
        """相談セッションを開始する."""
        # カートが空でないことを確認
        if cart.is_empty():
            raise CartEmptyError("カートが空です")

        # 各買い目の締め切りをチェック
        now = datetime.now()
        check_result = self._deadline_checker.check_deadlines(race_references, now)
        if not check_result.all_valid:
            raise DeadlinePassedError(
                "締め切りを過ぎた買い目があります",
                check_result.expired_items,
            )

        # セッションを作成し開始
        session = ConsultationSession.create(user_id=user_id)
        session.start(cart.get_items())

        # フィードバックを生成
        data_feedbacks = self._feedback_generator.generate_data_feedbacks(
            cart.get_items()
        )
        session.set_data_feedbacks(data_feedbacks)

        amount_feedback = self._feedback_generator.generate_amount_feedback(
            total_amount=cart.get_total_amount(),
            remaining_loss_limit=remaining_loss_limit,
        )
        session.set_amount_feedback(amount_feedback)

        return session

    def continue_conversation(
        self,
        session: ConsultationSession,
        user_message: str,
    ) -> ConsultationSession:
        """相談を継続する."""
        from ..enums import SessionStatus

        if session.status != SessionStatus.IN_PROGRESS:
            raise SessionNotInProgressError("セッションが進行中ではありません")

        # ユーザーメッセージを追加
        session.add_user_message(user_message)

        # AIレスポンスを生成
        context = ConsultationContext(
            cart_summary=self._summarize_cart(session),
            data_feedback_summary=self._summarize_data_feedbacks(session),
            amount_feedback_summary=self._summarize_amount_feedback(session),
        )
        ai_response = self._ai_client.generate_conversation_response(
            session.get_messages(),
            context,
        )

        # AIメッセージを追加
        session.add_ai_message(ai_response)

        return session

    def end_consultation(self, session: ConsultationSession) -> ConsultationSession:
        """相談セッションを終了する."""
        session.end()
        return session

    def _summarize_cart(self, session: ConsultationSession) -> str:
        """カートの内容を要約する."""
        items = session.get_cart_snapshot()
        if not items:
            return "カートは空です"

        summaries = []
        for item in items:
            bet = item.bet_selection
            summary = (
                f"{item.race_name}: "
                f"{bet.bet_type.get_display_name()} "
                f"{bet.horse_numbers.to_display_string()} "
                f"{bet.amount.format()}"
            )
            summaries.append(summary)
        return "\n".join(summaries)

    def _summarize_data_feedbacks(self, session: ConsultationSession) -> str:
        """データフィードバックを要約する."""
        feedbacks = session.get_data_feedbacks()
        if not feedbacks:
            return "フィードバックなし"

        summaries = [fb.overall_comment for fb in feedbacks]
        return "\n".join(summaries)

    def _summarize_amount_feedback(self, session: ConsultationSession) -> str:
        """掛け金フィードバックを要約する."""
        feedback = session.get_amount_feedback()
        if not feedback:
            return "フィードバックなし"
        return feedback.comment
