"""PurchaseOrderのテスト."""
import pytest

from src.domain.entities import PurchaseOrder
from src.domain.enums import IpatBetType, IpatVenueCode, PurchaseStatus
from src.domain.identifiers import CartId, PurchaseId, UserId
from src.domain.value_objects import IpatBetLine, Money


def _make_bet_lines() -> list[IpatBetLine]:
    """テスト用のIpatBetLineリストを生成する."""
    return [
        IpatBetLine(
            opdt="20260201",
            venue_code=IpatVenueCode.TOKYO,
            race_number=11,
            bet_type=IpatBetType.TANSYO,
            number="03",
            amount=100,
        ),
        IpatBetLine(
            opdt="20260201",
            venue_code=IpatVenueCode.TOKYO,
            race_number=11,
            bet_type=IpatBetType.UMAREN,
            number="01-03",
            amount=500,
        ),
    ]


class TestPurchaseOrder:
    """PurchaseOrderの単体テスト."""

    def test_createで生成できる(self) -> None:
        """createファクトリメソッドでPurchaseOrderを生成できることを確認."""
        user_id = UserId("user-1")
        cart_id = CartId("cart-1")
        bet_lines = _make_bet_lines()
        total_amount = Money.of(600)

        order = PurchaseOrder.create(
            user_id=user_id,
            cart_id=cart_id,
            bet_lines=bet_lines,
            total_amount=total_amount,
        )

        assert order.user_id == user_id
        assert order.cart_id == cart_id
        assert order.bet_lines == bet_lines
        assert order.total_amount == total_amount
        assert order.status == PurchaseStatus.PENDING
        assert order.error_message is None
        assert order.id is not None

    def test_mark_submittedでステータスがSUBMITTEDになる(self) -> None:
        """mark_submittedでステータスがSUBMITTEDに変更されることを確認."""
        order = PurchaseOrder.create(
            user_id=UserId("user-1"),
            cart_id=CartId("cart-1"),
            bet_lines=_make_bet_lines(),
            total_amount=Money.of(600),
        )
        order.mark_submitted()
        assert order.status == PurchaseStatus.SUBMITTED

    def test_mark_completedでステータスがCOMPLETEDになる(self) -> None:
        """mark_completedでステータスがCOMPLETEDに変更されることを確認."""
        order = PurchaseOrder.create(
            user_id=UserId("user-1"),
            cart_id=CartId("cart-1"),
            bet_lines=_make_bet_lines(),
            total_amount=Money.of(600),
        )
        order.mark_submitted()
        order.mark_completed()
        assert order.status == PurchaseStatus.COMPLETED

    def test_mark_failedでステータスがFAILEDになりエラーメッセージが設定される(self) -> None:
        """mark_failedでステータスがFAILEDに変更されエラーメッセージが設定されることを確認."""
        order = PurchaseOrder.create(
            user_id=UserId("user-1"),
            cart_id=CartId("cart-1"),
            bet_lines=_make_bet_lines(),
            total_amount=Money.of(600),
        )
        order.mark_failed("IPAT通信エラー")
        assert order.status == PurchaseStatus.FAILED
        assert order.error_message == "IPAT通信エラー"

    def test_created_atが設定される(self) -> None:
        """生成時にcreated_atが設定されることを確認."""
        order = PurchaseOrder.create(
            user_id=UserId("user-1"),
            cart_id=CartId("cart-1"),
            bet_lines=_make_bet_lines(),
            total_amount=Money.of(600),
        )
        assert order.created_at is not None

    def test_mark_submittedでupdated_atが更新される(self) -> None:
        """mark_submittedでupdated_atが更新されることを確認."""
        order = PurchaseOrder.create(
            user_id=UserId("user-1"),
            cart_id=CartId("cart-1"),
            bet_lines=_make_bet_lines(),
            total_amount=Money.of(600),
        )
        original_updated = order.updated_at
        order.mark_submitted()
        assert order.updated_at >= original_updated
