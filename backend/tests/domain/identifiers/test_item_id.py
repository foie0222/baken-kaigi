"""ItemIdのテスト."""
import pytest

from src.domain.identifiers import ItemId


class TestItemId:
    """ItemIdの単体テスト."""

    def test_値を指定して生成できる(self) -> None:
        """文字列値を指定してItemIdを生成できることを確認."""
        item_id = ItemId("item-123")
        assert item_id.value == "item-123"

    def test_空文字列で生成するとエラー(self) -> None:
        """空文字列を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ItemId("")

    def test_generateで新しいIDを生成できる(self) -> None:
        """generateメソッドでUUID形式のIDが生成されることを確認."""
        item_id = ItemId.generate()
        assert item_id.value is not None
        assert len(item_id.value) == 36

    def test_文字列変換でvalueが返る(self) -> None:
        """str()でvalue属性の値が返ることを確認."""
        item_id = ItemId("my-item")
        assert str(item_id) == "my-item"

    def test_不変オブジェクトである(self) -> None:
        """ItemIdは不変（frozen）であることを確認."""
        item_id = ItemId("test")
        with pytest.raises(AttributeError):
            item_id.value = "changed"  # type: ignore
