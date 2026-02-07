"""CartToIpatConverterのテスト."""
import pytest

from src.domain.entities import Cart
from src.domain.enums import BetType, IpatBetType, IpatVenueCode
from src.domain.identifiers import RaceId, UserId
from src.domain.services import CartToIpatConverter
from src.domain.value_objects import BetSelection, HorseNumbers, Money


class TestCartToIpatConverter:
    """CartToIpatConverterの単体テスト."""

    def _make_cart_with_selection(self, bet_type: BetType, numbers: list[int], amount: int = 100) -> Cart:
        """指定された買い目を1件持つカートを生成する."""
        cart = Cart.create(user_id=UserId("user-1"))
        cart.add_item(
            race_id=RaceId("race-1"),
            race_name="テストレース",
            bet_selection=BetSelection(
                bet_type=bet_type,
                horse_numbers=HorseNumbers.from_list(numbers),
                amount=Money.of(amount),
            ),
        )
        return cart

    def test_単勝の変換(self) -> None:
        """単勝のCartItemがIpatBetLineに正しく変換されることを確認."""
        cart = self._make_cart_with_selection(BetType.WIN, [3])
        lines = CartToIpatConverter.convert(cart, "20260201", "05", 11)

        assert len(lines) == 1
        line = lines[0]
        assert line.opdt == "20260201"
        assert line.venue_code == IpatVenueCode.TOKYO
        assert line.race_number == 11
        assert line.bet_type == IpatBetType.TANSYO
        assert line.number == "03"
        assert line.amount == 100

    def test_複勝の変換(self) -> None:
        """複勝のCartItemがIpatBetLineに正しく変換されることを確認."""
        cart = self._make_cart_with_selection(BetType.PLACE, [5])
        lines = CartToIpatConverter.convert(cart, "20260201", "06", 1)

        assert len(lines) == 1
        assert lines[0].bet_type == IpatBetType.FUKUSYO
        assert lines[0].number == "05"

    def test_馬連の変換_昇順ソート(self) -> None:
        """馬連のCartItemが昇順ソートされたIpatBetLineに変換されることを確認."""
        cart = self._make_cart_with_selection(BetType.QUINELLA, [5, 3])
        lines = CartToIpatConverter.convert(cart, "20260201", "05", 11)

        assert lines[0].bet_type == IpatBetType.UMAREN
        assert lines[0].number == "03-05"  # 昇順ソート

    def test_ワイドの変換_昇順ソート(self) -> None:
        """ワイドのCartItemが昇順ソートされたIpatBetLineに変換されることを確認."""
        cart = self._make_cart_with_selection(BetType.QUINELLA_PLACE, [8, 2])
        lines = CartToIpatConverter.convert(cart, "20260201", "05", 11)

        assert lines[0].bet_type == IpatBetType.WIDE
        assert lines[0].number == "02-08"  # 昇順ソート

    def test_馬単の変換_着順維持(self) -> None:
        """馬単のCartItemが着順を維持したIpatBetLineに変換されることを確認."""
        cart = self._make_cart_with_selection(BetType.EXACTA, [5, 3])
        lines = CartToIpatConverter.convert(cart, "20260201", "05", 11)

        assert lines[0].bet_type == IpatBetType.UMATAN
        assert lines[0].number == "05-03"  # 着順維持

    def test_三連複の変換_昇順ソート(self) -> None:
        """三連複のCartItemが昇順ソートされたIpatBetLineに変換されることを確認."""
        cart = self._make_cart_with_selection(BetType.TRIO, [7, 3, 1])
        lines = CartToIpatConverter.convert(cart, "20260201", "09", 12)

        assert lines[0].bet_type == IpatBetType.SANRENPUKU
        assert lines[0].number == "01-03-07"  # 昇順ソート

    def test_三連単の変換_着順維持(self) -> None:
        """三連単のCartItemが着順を維持したIpatBetLineに変換されることを確認."""
        cart = self._make_cart_with_selection(BetType.TRIFECTA, [7, 3, 1])
        lines = CartToIpatConverter.convert(cart, "20260201", "09", 12)

        assert lines[0].bet_type == IpatBetType.SANRENTAN
        assert lines[0].number == "07-03-01"  # 着順維持

    def test_複数アイテムの変換(self) -> None:
        """複数のCartItemが正しく変換されることを確認."""
        cart = Cart.create(user_id=UserId("user-1"))
        cart.add_item(
            race_id=RaceId("race-1"),
            race_name="テストレース",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers.of(3),
                amount=Money.of(100),
            ),
        )
        cart.add_item(
            race_id=RaceId("race-1"),
            race_name="テストレース",
            bet_selection=BetSelection(
                bet_type=BetType.QUINELLA,
                horse_numbers=HorseNumbers.of(3, 5),
                amount=Money.of(500),
            ),
        )

        lines = CartToIpatConverter.convert(cart, "20260201", "05", 11)
        assert len(lines) == 2

    def test_馬番が2桁ゼロ埋め(self) -> None:
        """馬番が2桁ゼロ埋めされることを確認."""
        cart = self._make_cart_with_selection(BetType.WIN, [1])
        lines = CartToIpatConverter.convert(cart, "20260201", "05", 1)
        assert lines[0].number == "01"

    def test_2桁馬番のゼロ埋め(self) -> None:
        """2桁の馬番でもゼロ埋めが正しいことを確認."""
        cart = self._make_cart_with_selection(BetType.WIN, [12])
        lines = CartToIpatConverter.convert(cart, "20260201", "05", 1)
        assert lines[0].number == "12"
