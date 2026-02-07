"""PurchaseIdのテスト."""
import pytest

from src.domain.identifiers import PurchaseId


class TestPurchaseId:
    """PurchaseIdの単体テスト."""

    def test_値を指定して生成できる(self) -> None:
        """文字列値を指定してPurchaseIdを生成できることを確認."""
        pid = PurchaseId("test-id")
        assert pid.value == "test-id"

    def test_空文字でエラー(self) -> None:
        """空文字列でValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PurchaseId("")

    def test_generateで生成できる(self) -> None:
        """generateメソッドで新しいPurchaseIdを生成できることを確認."""
        pid = PurchaseId.generate()
        assert pid.value
        assert len(pid.value) == 36  # UUID format

    def test_generateで一意なIDが生成される(self) -> None:
        """generateメソッドで異なるIDが生成されることを確認."""
        pid1 = PurchaseId.generate()
        pid2 = PurchaseId.generate()
        assert pid1 != pid2

    def test_strで値が返る(self) -> None:
        """str()で値が返ることを確認."""
        pid = PurchaseId("test-id")
        assert str(pid) == "test-id"

    def test_不変オブジェクトである(self) -> None:
        """PurchaseIdは不変（frozen）であることを確認."""
        pid = PurchaseId("test-id")
        with pytest.raises(AttributeError):
            pid.value = "new-id"  # type: ignore
