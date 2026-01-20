"""メッセージ送信ユースケース."""
from dataclasses import dataclass

from src.domain.entities import Message
from src.domain.enums import SessionStatus
from src.domain.identifiers import SessionId
from src.domain.ports import AIClient, ConsultationContext, ConsultationSessionRepository


class SessionNotFoundError(Exception):
    """セッションが見つからないエラー."""

    def __init__(self, session_id: SessionId) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class SessionNotInProgressError(Exception):
    """セッションが進行中でないエラー."""

    def __init__(self, session_id: SessionId) -> None:
        self.session_id = session_id
        super().__init__(f"Session is not in progress: {session_id}")


@dataclass(frozen=True)
class SendMessageResult:
    """メッセージ送信結果."""

    user_message: Message
    ai_message: Message
    messages: list[Message]


class SendMessageUseCase:
    """AIにメッセージを送信するユースケース."""

    def __init__(
        self,
        session_repository: ConsultationSessionRepository,
        ai_client: AIClient,
    ) -> None:
        """初期化.

        Args:
            session_repository: セッションリポジトリ
            ai_client: AIクライアント
        """
        self._session_repository = session_repository
        self._ai_client = ai_client

    def execute(self, session_id: SessionId, content: str) -> SendMessageResult:
        """メッセージを送信してAI応答を取得する.

        Args:
            session_id: セッションID
            content: メッセージ内容

        Returns:
            メッセージ送信結果

        Raises:
            SessionNotFoundError: セッションが見つからない場合
            SessionNotInProgressError: セッションが進行中でない場合
        """
        session = self._session_repository.find_by_id(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)

        if session.status != SessionStatus.IN_PROGRESS:
            raise SessionNotInProgressError(session_id)

        # ユーザーメッセージを追加
        user_message = session.add_user_message(content)

        # コンテキストを構築
        context = self._build_context(session)

        # AI応答を生成
        ai_response = self._ai_client.generate_conversation_response(
            session.get_messages(), context
        )

        # AIメッセージを追加
        ai_message = session.add_ai_message(ai_response)

        # セッションを保存
        self._session_repository.save(session)

        return SendMessageResult(
            user_message=user_message,
            ai_message=ai_message,
            messages=session.get_messages(),
        )

    def _build_context(self, session) -> ConsultationContext:
        """会話コンテキストを構築する."""
        # カートサマリーを構築
        cart_items = session.get_cart_snapshot()
        cart_lines = []
        for item in cart_items:
            line = f"{item.race_name}: {item.bet_selection.bet_type.value} {item.bet_selection.horse_numbers} {item.get_amount().format()}"
            cart_lines.append(line)
        cart_summary = "\n".join(cart_lines)

        # データフィードバックサマリーを構築
        data_feedbacks = session.get_data_feedbacks()
        feedback_lines = []
        for fb in data_feedbacks:
            feedback_lines.append(fb.overall_comment)
        data_feedback_summary = "\n".join(feedback_lines)

        # 掛け金フィードバックサマリーを構築
        amount_fb = session.get_amount_feedback()
        amount_feedback_summary = amount_fb.comment if amount_fb else ""

        return ConsultationContext(
            cart_summary=cart_summary,
            data_feedback_summary=data_feedback_summary,
            amount_feedback_summary=amount_feedback_summary,
        )
