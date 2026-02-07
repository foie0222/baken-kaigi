"""カートからIPAT投票行への変換ドメインサービス."""
from ..entities import Cart
from ..enums import IpatBetType, IpatVenueCode
from ..value_objects import IpatBetLine


class CartToIpatConverter:
    """CartItemをIpatBetLineに変換するサービス."""

    @staticmethod
    def convert(
        cart: Cart,
        race_date: str,
        course_code: str,
        race_number: int,
    ) -> list[IpatBetLine]:
        """カート内の全アイテムをIpatBetLineに変換する."""
        venue_code = IpatVenueCode.from_course_code(course_code)
        lines = []

        for item in cart.get_items():
            bet_type = IpatBetType.from_bet_type(item.get_bet_type())
            numbers = item.get_selected_numbers().to_list()

            # 馬連/ワイド/三連複は昇順ソート、馬単/三連単は着順維持
            if not item.get_bet_type().is_order_required():
                numbers = sorted(numbers)

            number_str = "-".join(f"{n:02d}" for n in numbers)

            lines.append(
                IpatBetLine(
                    opdt=race_date,
                    venue_code=venue_code,
                    race_number=race_number,
                    bet_type=bet_type,
                    number=number_str,
                    amount=item.get_amount().value,
                )
            )

        return lines
