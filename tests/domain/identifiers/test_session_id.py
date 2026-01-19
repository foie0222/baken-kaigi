"""SessionIdのテスト."""
import pytest

from src.domain.identifiers import SessionId


class TestSessionId:
    """SessionIdの単体テスト."""

    def test_値を指定して生成できる(self) -> None:
        """文字列値を指定してSessionIdを生成できることを確認."""
        session_id = SessionId("session-123")
        assert session_id.value == "session-123"

    def test_空文字列で生成するとエラー(self) -> None:
        """空文字列を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SessionId("")

    def test_generateで新しいIDを生成できる(self) -> None:
        """generateメソッドでUUID形式のIDが生成されることを確認."""
        session_id = SessionId.generate()
        assert session_id.value is not None
        assert len(session_id.value) == 36

    def test_文字列変換でvalueが返る(self) -> None:
        """str()でvalue属性の値が返ることを確認."""
        session_id = SessionId("my-session")
        assert str(session_id) == "my-session"

    def test_不変オブジェクトである(self) -> None:
        """SessionIdは不変（frozen）であることを確認."""
        session_id = SessionId("test")
        with pytest.raises(AttributeError):
            session_id.value = "changed"  # type: ignore
