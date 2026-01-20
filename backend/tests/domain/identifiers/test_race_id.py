"""RaceIdのテスト."""
import pytest

from src.domain.identifiers import RaceId


class TestRaceId:
    """RaceIdの単体テスト."""

    def test_値を指定して生成できる(self) -> None:
        """文字列値を指定してRaceIdを生成できることを確認."""
        race_id = RaceId("2024010101")
        assert race_id.value == "2024010101"

    def test_空文字列で生成するとエラー(self) -> None:
        """空文字列を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            RaceId("")

    def test_文字列変換でvalueが返る(self) -> None:
        """str()でvalue属性の値が返ることを確認."""
        race_id = RaceId("race-001")
        assert str(race_id) == "race-001"

    def test_同じ値のRaceIdは等価(self) -> None:
        """同じvalue値を持つRaceIdは等しいと判定されることを確認."""
        id1 = RaceId("same-race")
        id2 = RaceId("same-race")
        assert id1 == id2

    def test_不変オブジェクトである(self) -> None:
        """RaceIdは不変（frozen）であることを確認."""
        race_id = RaceId("test")
        with pytest.raises(AttributeError):
            race_id.value = "changed"  # type: ignore
