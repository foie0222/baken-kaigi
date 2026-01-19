"""CartIdのテスト."""
import pytest

from src.domain.identifiers import CartId


class TestCartId:
    """CartIdの単体テスト."""

    def test_値を指定して生成できる(self) -> None:
        """文字列値を指定してCartIdを生成できることを確認."""
        cart_id = CartId("test-id-123")
        assert cart_id.value == "test-id-123"

    def test_空文字列で生成するとエラー(self) -> None:
        """空文字列を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            CartId("")

    def test_generateで新しいIDを生成できる(self) -> None:
        """generateメソッドでUUID形式のIDが生成されることを確認."""
        cart_id = CartId.generate()
        assert cart_id.value is not None
        assert len(cart_id.value) == 36  # UUID形式

    def test_generateは毎回異なるIDを生成する(self) -> None:
        """generateメソッドは呼び出しごとに異なるIDを生成することを確認."""
        id1 = CartId.generate()
        id2 = CartId.generate()
        assert id1 != id2

    def test_文字列変換でvalueが返る(self) -> None:
        """str()でvalue属性の値が返ることを確認."""
        cart_id = CartId("my-cart")
        assert str(cart_id) == "my-cart"

    def test_同じ値のCartIdは等価(self) -> None:
        """同じvalue値を持つCartIdは等しいと判定されることを確認."""
        id1 = CartId("same-id")
        id2 = CartId("same-id")
        assert id1 == id2

    def test_不変オブジェクトである(self) -> None:
        """CartIdは不変（frozen）であることを確認."""
        cart_id = CartId("test")
        with pytest.raises(AttributeError):
            cart_id.value = "changed"  # type: ignore
