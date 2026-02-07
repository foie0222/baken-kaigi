"""SubmitPurchaseUseCase のテスト."""
import pytest

from src.application.use_cases.submit_purchase import (
    SubmitPurchaseUseCase,
    CartNotFoundError,
    CredentialsNotFoundError,
    InsufficientBalanceError,
    IpatSubmissionError,
)
from src.domain.entities import Cart
from src.domain.enums import BetType
from src.domain.identifiers import CartId, RaceId, UserId
from src.domain.value_objects import BetSelection, HorseNumbers, Money
from src.infrastructure.providers.in_memory_credentials_provider import (
    InMemoryCredentialsProvider,
)
from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway
from src.infrastructure.providers.stub_spending_limit_provider import (
    StubSpendingLimitProvider,
)
from src.infrastructure.repositories.in_memory_cart_repository import (
    InMemoryCartRepository,
)
from src.infrastructure.repositories.in_memory_purchase_order_repository import (
    InMemoryPurchaseOrderRepository,
)
from src.domain.value_objects import IpatCredentials


def _make_cart(user_id: str = "user-001", cart_id: str = "cart-001") -> Cart:
    cart = Cart(
        cart_id=CartId(cart_id),
        user_id=UserId(user_id),
    )
    cart.add_item(
        race_id=RaceId("202605051211"),
        race_name="東京11R",
        bet_selection=BetSelection(
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(1),
            amount=Money.of(100),
        ),
    )
    return cart


def _make_credentials() -> IpatCredentials:
    return IpatCredentials(
        card_number="123456789012",
        birthday="19900101",
        pin="1234",
        dummy_pin="5678",
    )


def _make_use_case(
    cart_repo=None,
    order_repo=None,
    gateway=None,
    cred_provider=None,
    spending_provider=None,
):
    return SubmitPurchaseUseCase(
        cart_repository=cart_repo or InMemoryCartRepository(),
        purchase_order_repository=order_repo or InMemoryPurchaseOrderRepository(),
        ipat_gateway=gateway or MockIpatGateway(),
        credentials_provider=cred_provider or InMemoryCredentialsProvider(),
        spending_limit_provider=spending_provider or StubSpendingLimitProvider(),
    )


class TestSubmitPurchaseUseCase:
    """SubmitPurchaseUseCase のテスト."""

    def test_正常購入(self) -> None:
        cart_repo = InMemoryCartRepository()
        order_repo = InMemoryPurchaseOrderRepository()
        cred_provider = InMemoryCredentialsProvider()
        cart = _make_cart()
        cart_repo.save(cart)
        user_id = UserId("user-001")
        cred_provider.save_credentials(user_id, _make_credentials())

        use_case = _make_use_case(
            cart_repo=cart_repo,
            order_repo=order_repo,
            cred_provider=cred_provider,
        )
        order = use_case.execute(
            user_id="user-001",
            cart_id="cart-001",
            race_date="20260207",
            course_code="05",
            race_number=11,
        )
        assert order.status.value == "completed"
        assert order.total_amount.value == 100

        saved = order_repo.find_by_id(order.id)
        assert saved is not None

    def test_カートなしでエラー(self) -> None:
        use_case = _make_use_case()
        with pytest.raises(CartNotFoundError):
            use_case.execute(
                user_id="user-001",
                cart_id="nonexistent",
                race_date="20260207",
                course_code="05",
                race_number=11,
            )

    def test_認証情報なしでエラー(self) -> None:
        cart_repo = InMemoryCartRepository()
        cart = _make_cart()
        cart_repo.save(cart)

        use_case = _make_use_case(cart_repo=cart_repo)
        with pytest.raises(CredentialsNotFoundError):
            use_case.execute(
                user_id="user-001",
                cart_id="cart-001",
                race_date="20260207",
                course_code="05",
                race_number=11,
            )

    def test_残高不足でエラー(self) -> None:
        from unittest.mock import MagicMock
        from src.domain.value_objects import IpatBalance

        cart_repo = InMemoryCartRepository()
        cred_provider = InMemoryCredentialsProvider()
        cart = _make_cart()
        cart_repo.save(cart)
        cred_provider.save_credentials(UserId("user-001"), _make_credentials())

        mock_gateway = MagicMock()
        mock_gateway.get_balance.return_value = IpatBalance(
            bet_dedicated_balance=0,
            settle_possible_balance=0,
            bet_balance=0,
            limit_vote_amount=0,
        )

        use_case = _make_use_case(
            cart_repo=cart_repo,
            cred_provider=cred_provider,
            gateway=mock_gateway,
        )
        with pytest.raises(InsufficientBalanceError):
            use_case.execute(
                user_id="user-001",
                cart_id="cart-001",
                race_date="20260207",
                course_code="05",
                race_number=11,
            )

    def test_IPAT投票失敗でエラー(self) -> None:
        from unittest.mock import MagicMock
        from src.domain.value_objects import IpatBalance

        cart_repo = InMemoryCartRepository()
        order_repo = InMemoryPurchaseOrderRepository()
        cred_provider = InMemoryCredentialsProvider()
        cart = _make_cart()
        cart_repo.save(cart)
        cred_provider.save_credentials(UserId("user-001"), _make_credentials())

        mock_gateway = MagicMock()
        mock_gateway.get_balance.return_value = IpatBalance(
            bet_dedicated_balance=100000,
            settle_possible_balance=100000,
            bet_balance=100000,
            limit_vote_amount=100000,
        )
        mock_gateway.submit_bets.return_value = False

        use_case = _make_use_case(
            cart_repo=cart_repo,
            order_repo=order_repo,
            cred_provider=cred_provider,
            gateway=mock_gateway,
        )
        with pytest.raises(IpatSubmissionError):
            use_case.execute(
                user_id="user-001",
                cart_id="cart-001",
                race_date="20260207",
                course_code="05",
                race_number=11,
            )
