"""列挙型（MessageType, SessionStatus, WarningLevel）のテスト."""
from src.domain.enums import MessageType
from src.domain.enums import SessionStatus
from src.domain.enums import WarningLevel


class TestMessageType:
    """MessageTypeの単体テスト."""

    def test_USERが定義されている(self) -> None:
        """USERメンバーが存在することを確認."""
        assert MessageType.USER.value == "user"

    def test_AIが定義されている(self) -> None:
        """AIメンバーが存在することを確認."""
        assert MessageType.AI.value == "ai"

    def test_SYSTEMが定義されている(self) -> None:
        """SYSTEMメンバーが存在することを確認."""
        assert MessageType.SYSTEM.value == "system"


class TestSessionStatus:
    """SessionStatusの単体テスト."""

    def test_NOT_STARTEDが定義されている(self) -> None:
        """NOT_STARTEDメンバーが存在することを確認."""
        assert SessionStatus.NOT_STARTED.value == "not_started"

    def test_IN_PROGRESSが定義されている(self) -> None:
        """IN_PROGRESSメンバーが存在することを確認."""
        assert SessionStatus.IN_PROGRESS.value == "in_progress"

    def test_COMPLETEDが定義されている(self) -> None:
        """COMPLETEDメンバーが存在することを確認."""
        assert SessionStatus.COMPLETED.value == "completed"


class TestWarningLevel:
    """WarningLevelの単体テスト."""

    def test_NONEが定義されている(self) -> None:
        """NONEメンバーが存在することを確認."""
        assert WarningLevel.NONE.value == "none"

    def test_CAUTIONが定義されている(self) -> None:
        """CAUTIONメンバーが存在することを確認."""
        assert WarningLevel.CAUTION.value == "caution"

    def test_WARNINGが定義されている(self) -> None:
        """WARNINGメンバーが存在することを確認."""
        assert WarningLevel.WARNING.value == "warning"
