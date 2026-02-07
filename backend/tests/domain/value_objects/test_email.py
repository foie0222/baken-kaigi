"""Email値オブジェクトのテスト."""
import pytest

from src.domain.value_objects import Email


class TestEmail:
    """Emailのテスト."""

    def test_有効なメールアドレスで生成できる(self):
        email = Email("test@example.com")
        assert email.value == "test@example.com"

    def test_空文字でValueErrorが発生する(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Email("")

    def test_不正な形式でValueErrorが発生する(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("invalid-email")

    def test_アットマークなしでValueErrorが発生する(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("testexample.com")

    def test_ドメインなしでValueErrorが発生する(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("test@")

    def test_str表現(self):
        email = Email("test@example.com")
        assert str(email) == "test@example.com"

    def test_等価性(self):
        email1 = Email("test@example.com")
        email2 = Email("test@example.com")
        assert email1 == email2

    def test_不変性(self):
        email = Email("test@example.com")
        with pytest.raises(AttributeError):
            email.value = "other@example.com"  # type: ignore

    def test_サブドメイン付きメールアドレス(self):
        email = Email("user@sub.example.com")
        assert email.value == "user@sub.example.com"

    def test_プラス記号付きメールアドレス(self):
        email = Email("user+tag@example.com")
        assert email.value == "user+tag@example.com"
