"""DisplayName値オブジェクトのテスト."""
import pytest

from src.domain.value_objects import DisplayName


class TestDisplayName:
    """DisplayNameのテスト."""

    def test_有効な名前で生成できる(self):
        name = DisplayName("太郎")
        assert name.value == "太郎"

    def test_空文字でValueErrorが発生する(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            DisplayName("")

    def test_スペースのみでValueErrorが発生する(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            DisplayName("   ")

    def test_50文字で生成できる(self):
        name = DisplayName("a" * 50)
        assert len(name.value) == 50

    def test_51文字でValueErrorが発生する(self):
        with pytest.raises(ValueError, match="at most 50"):
            DisplayName("a" * 51)

    def test_1文字で生成できる(self):
        name = DisplayName("a")
        assert name.value == "a"

    def test_str表現(self):
        name = DisplayName("太郎")
        assert str(name) == "太郎"

    def test_等価性(self):
        name1 = DisplayName("太郎")
        name2 = DisplayName("太郎")
        assert name1 == name2

    def test_不変性(self):
        name = DisplayName("太郎")
        with pytest.raises(AttributeError):
            name.value = "花子"  # type: ignore
