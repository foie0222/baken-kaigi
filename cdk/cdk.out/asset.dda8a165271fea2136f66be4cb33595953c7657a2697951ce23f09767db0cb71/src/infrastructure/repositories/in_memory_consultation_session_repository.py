"""相談セッションリポジトリのインメモリ実装."""
from src.domain.entities import ConsultationSession
from src.domain.identifiers import SessionId, UserId
from src.domain.ports import ConsultationSessionRepository


class InMemoryConsultationSessionRepository(ConsultationSessionRepository):
    """相談セッションリポジトリのインメモリ実装."""

    def __init__(self) -> None:
        """初期化."""
        self._sessions: dict[str, ConsultationSession] = {}

    def save(self, session: ConsultationSession) -> None:
        """セッションを保存する."""
        self._sessions[session.session_id.value] = session

    def find_by_id(self, session_id: SessionId) -> ConsultationSession | None:
        """セッションIDで検索する."""
        return self._sessions.get(session_id.value)

    def find_by_user_id(self, user_id: UserId) -> list[ConsultationSession]:
        """ユーザーIDで検索する."""
        result = []
        for session in self._sessions.values():
            if session.user_id is not None and session.user_id == user_id:
                result.append(session)
        return result

    def delete(self, session_id: SessionId) -> None:
        """セッションを削除する."""
        self._sessions.pop(session_id.value, None)
