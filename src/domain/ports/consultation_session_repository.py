"""相談セッションリポジトリインターフェース."""
from abc import ABC, abstractmethod

from ..entities import ConsultationSession
from ..identifiers import SessionId, UserId


class ConsultationSessionRepository(ABC):
    """相談セッションリポジトリのインターフェース."""

    @abstractmethod
    def save(self, session: ConsultationSession) -> None:
        """セッションを保存する."""
        pass

    @abstractmethod
    def find_by_id(self, session_id: SessionId) -> ConsultationSession | None:
        """セッションIDで検索する."""
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: UserId) -> list[ConsultationSession]:
        """ユーザーIDで検索する（複数セッションがある場合がある）."""
        pass

    @abstractmethod
    def delete(self, session_id: SessionId) -> None:
        """セッションを削除する."""
        pass
