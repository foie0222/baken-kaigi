"""UserIdのテスト."""
import pytest

from src.domain.identifiers import UserId


class TestUserId:
    """UserIdの単体テスト."""

    def test_値を指定して生成できる(self) -> None:
        """文字列値を指定してUserIdを生成できることを確認."""
        user_id = UserId("user-001")
        assert user_id.value == "user-001"

    def test_空文字列で生成するとエラー(self) -> None:
        """空文字列を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            UserId("")

    def test_文字列変換でvalueが返る(self) -> None:
        """str()でvalue属性の値が返ることを確認."""
        user_id = UserId("my-user")
        assert str(user_id) == "my-user"

    def test_同じ値のUserIdは等価(self) -> None:
        """同じvalue値を持つUserIdは等しいと判定されることを確認."""
        id1 = UserId("same-user")
        id2 = UserId("same-user")
        assert id1 == id2

    def test_不変オブジェクトである(self) -> None:
        """UserIdは不変（frozen）であることを確認."""
        user_id = UserId("test")
        with pytest.raises(AttributeError):
            user_id.value = "changed"  # type: ignore
