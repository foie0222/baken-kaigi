"""HorseNumbersのテスト."""
import pytest

from src.domain.value_objects import HorseNumbers


class TestHorseNumbers:
    """HorseNumbersの単体テスト."""

    def test_有効な馬番で生成できる(self) -> None:
        """1〜18の範囲の馬番で生成できることを確認."""
        numbers = HorseNumbers((1, 5, 10))
        assert numbers.numbers == (1, 5, 10)

    def test_ofで可変長引数から生成できる(self) -> None:
        """ofメソッドで可変長引数から生成できることを確認."""
        numbers = HorseNumbers.of(3, 7, 12)
        assert numbers.numbers == (3, 7, 12)

    def test_from_listでリストから生成できる(self) -> None:
        """from_listメソッドでリストから生成できることを確認."""
        numbers = HorseNumbers.from_list([2, 4, 6])
        assert numbers.numbers == (2, 4, 6)

    def test_範囲外の馬番でエラー_0(self) -> None:
        """0を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="between 1 and 18"):
            HorseNumbers((0, 1, 2))

    def test_範囲外の馬番でエラー_19(self) -> None:
        """19を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="between 1 and 18"):
            HorseNumbers((1, 2, 19))

    def test_重複馬番でエラー(self) -> None:
        """重複する馬番を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="duplicates"):
            HorseNumbers((1, 1, 2))

    def test_countで馬番数を取得(self) -> None:
        """countメソッドで選択馬番数を取得できることを確認."""
        numbers = HorseNumbers.of(1, 2, 3)
        assert numbers.count() == 3

    def test_containsで馬番が含まれるか判定(self) -> None:
        """containsメソッドで馬番の有無を判定できることを確認."""
        numbers = HorseNumbers.of(1, 5, 10)
        assert numbers.contains(5) is True
        assert numbers.contains(3) is False

    def test_to_listでリストを取得(self) -> None:
        """to_listメソッドでリストを取得できることを確認."""
        numbers = HorseNumbers.of(3, 5, 8)
        assert numbers.to_list() == [3, 5, 8]

    def test_to_display_stringでハイフン区切り表示(self) -> None:
        """to_display_stringでハイフン区切りの文字列を取得できることを確認."""
        numbers = HorseNumbers.of(3, 5, 8)
        assert numbers.to_display_string() == "3-5-8"

    def test_str変換で表示用文字列(self) -> None:
        """str()で表示用文字列が返ることを確認."""
        numbers = HorseNumbers.of(1, 2)
        assert str(numbers) == "1-2"

    def test_不変オブジェクトである(self) -> None:
        """HorseNumbersは不変（frozen）であることを確認."""
        numbers = HorseNumbers.of(1, 2, 3)
        with pytest.raises(AttributeError):
            numbers.numbers = (4, 5, 6)  # type: ignore
