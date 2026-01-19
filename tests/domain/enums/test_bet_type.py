"""BetTypeのテスト."""
from src.domain.enums import BetType


class TestBetType:
    """BetTypeの単体テスト."""

    def test_単勝の必要頭数は1(self) -> None:
        """単勝(WIN)の必要選択頭数が1であることを確認."""
        assert BetType.WIN.get_required_count() == 1

    def test_複勝の必要頭数は1(self) -> None:
        """複勝(PLACE)の必要選択頭数が1であることを確認."""
        assert BetType.PLACE.get_required_count() == 1

    def test_馬連の必要頭数は2(self) -> None:
        """馬連(QUINELLA)の必要選択頭数が2であることを確認."""
        assert BetType.QUINELLA.get_required_count() == 2

    def test_ワイドの必要頭数は2(self) -> None:
        """ワイド(QUINELLA_PLACE)の必要選択頭数が2であることを確認."""
        assert BetType.QUINELLA_PLACE.get_required_count() == 2

    def test_馬単の必要頭数は2(self) -> None:
        """馬単(EXACTA)の必要選択頭数が2であることを確認."""
        assert BetType.EXACTA.get_required_count() == 2

    def test_三連複の必要頭数は3(self) -> None:
        """三連複(TRIO)の必要選択頭数が3であることを確認."""
        assert BetType.TRIO.get_required_count() == 3

    def test_三連単の必要頭数は3(self) -> None:
        """三連単(TRIFECTA)の必要選択頭数が3であることを確認."""
        assert BetType.TRIFECTA.get_required_count() == 3

    def test_単勝の日本語表示名(self) -> None:
        """単勝(WIN)の日本語表示名が「単勝」であることを確認."""
        assert BetType.WIN.get_display_name() == "単勝"

    def test_三連単の日本語表示名(self) -> None:
        """三連単(TRIFECTA)の日本語表示名が「三連単」であることを確認."""
        assert BetType.TRIFECTA.get_display_name() == "三連単"

    def test_馬単は順序が必要(self) -> None:
        """馬単(EXACTA)は順序が必要であることを確認."""
        assert BetType.EXACTA.is_order_required() is True

    def test_三連単は順序が必要(self) -> None:
        """三連単(TRIFECTA)は順序が必要であることを確認."""
        assert BetType.TRIFECTA.is_order_required() is True

    def test_馬連は順序不要(self) -> None:
        """馬連(QUINELLA)は順序不要であることを確認."""
        assert BetType.QUINELLA.is_order_required() is False

    def test_三連複は順序不要(self) -> None:
        """三連複(TRIO)は順序不要であることを確認."""
        assert BetType.TRIO.is_order_required() is False
