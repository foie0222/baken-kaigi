"""購入APIハンドラーのテスト."""
import json
from datetime import datetime

import pytest

from src.api.dependencies import Dependencies
from src.api.handlers.purchase import (
    get_purchase_detail_handler,
    get_purchase_history_handler,
    submit_purchase_handler,
)
from src.domain.entities import Cart, PurchaseOrder
from src.domain.enums import BetType, IpatBetType, IpatVenueCode, PurchaseStatus
from src.domain.identifiers import CartId, PurchaseId, RaceId, UserId
from src.domain.value_objects import BetSelection, HorseNumbers, IpatBetLine, IpatCredentials, Money
from src.infrastructure.providers.in_memory_credentials_provider import InMemoryCredentialsProvider
from src.domain.ports import IpatGatewayError
from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway
from src.infrastructure.providers.stub_spending_limit_provider import StubSpendingLimitProvider
from src.infrastructure.repositories.in_memory_cart_repository import InMemoryCartRepository
from src.infrastructure.repositories.in_memory_purchase_order_repository import InMemoryPurchaseOrderRepository


def _auth_event(user_id: str = "user-001", body: dict | None = None, path_params: dict | None = None) -> dict:
    event = {
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                }
            }
        },
    }
    if body is not None:
        event["body"] = json.dumps(body)
    if path_params is not None:
        event["pathParameters"] = path_params
    return event


def _setup_deps():
    Dependencies.reset()
    cart_repo = InMemoryCartRepository()
    order_repo = InMemoryPurchaseOrderRepository()
    cred_provider = InMemoryCredentialsProvider()
    gateway = MockIpatGateway()
    spending_provider = StubSpendingLimitProvider()

    Dependencies.set_cart_repository(cart_repo)
    Dependencies.set_purchase_order_repository(order_repo)
    Dependencies.set_ipat_gateway(gateway)
    Dependencies.set_credentials_provider(cred_provider)
    Dependencies.set_spending_limit_provider(spending_provider)

    return cart_repo, order_repo, cred_provider, gateway, spending_provider


class TestSubmitPurchaseHandler:
    """submit_purchase_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {"body": json.dumps({"cart_id": "cart-001"})}
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常購入(self) -> None:
        cart_repo, order_repo, cred_provider, _, _ = _setup_deps()

        cart = Cart(cart_id=CartId("cart-001"), user_id=UserId("user-001"))
        cart.add_item(
            race_id=RaceId("202605051211"),
            race_name="東京11R",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers.of(1),
                amount=Money.of(100),
            ),
        )
        cart_repo.save(cart)
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            ),
        )

        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert "purchase_id" in body
        assert body["status"] == "completed"

    def test_cart_id未指定で400(self) -> None:
        _setup_deps()
        event = _auth_event(body={})
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_IpatGatewayError発生時に500(self) -> None:
        cart_repo, _, cred_provider, gateway, _ = _setup_deps()

        cart = Cart(cart_id=CartId("cart-001"), user_id=UserId("user-001"))
        cart.add_item(
            race_id=RaceId("202605051211"),
            race_name="東京11R",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers.of(1),
                amount=Money.of(100),
            ),
        )
        cart_repo.save(cart)
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            ),
        )
        # ゲートウェイが例外を投げるように設定
        gateway.set_balance_error(IpatGatewayError("IPAT通信エラー"))

        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "IPAT通信エラー" in body["error"]["message"]

    def test_投票送信時IpatGatewayError発生で500(self) -> None:
        cart_repo, _, cred_provider, gateway, _ = _setup_deps()

        cart = Cart(cart_id=CartId("cart-001"), user_id=UserId("user-001"))
        cart.add_item(
            race_id=RaceId("202605051211"),
            race_name="東京11R",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers.of(1),
                amount=Money.of(100),
            ),
        )
        cart_repo.save(cart)
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            ),
        )
        # 投票送信時にエラーを発生させる設定
        gateway.set_submit_error(IpatGatewayError("投票送信失敗"))

        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "IPAT通信エラー" in body["error"]["message"]


class TestGetPurchaseHistoryHandler:
    """get_purchase_history_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {}
        result = get_purchase_history_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常取得(self) -> None:
        _, order_repo, _, _, _ = _setup_deps()
        order = PurchaseOrder(
            id=PurchaseId("p-001"),
            user_id=UserId("user-001"),
            cart_id=CartId("cart-001"),
            bet_lines=[
                IpatBetLine(
                    opdt="20260207",
                    venue_code=IpatVenueCode.TOKYO,
                    race_number=11,
                    bet_type=IpatBetType.TANSYO,
                    number="01",
                    amount=100,
                ),
            ],
            status=PurchaseStatus.COMPLETED,
            total_amount=Money.of(100),
            created_at=datetime(2026, 2, 7, 10, 0, 0),
            updated_at=datetime(2026, 2, 7, 10, 0, 0),
        )
        order_repo.save(order)

        event = _auth_event()
        result = get_purchase_history_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body) == 1


class TestGetPurchaseDetailHandler:
    """get_purchase_detail_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {"pathParameters": {"purchase_id": "p-001"}}
        result = get_purchase_detail_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常取得(self) -> None:
        _, order_repo, _, _, _ = _setup_deps()
        order = PurchaseOrder(
            id=PurchaseId("p-001"),
            user_id=UserId("user-001"),
            cart_id=CartId("cart-001"),
            bet_lines=[
                IpatBetLine(
                    opdt="20260207",
                    venue_code=IpatVenueCode.TOKYO,
                    race_number=11,
                    bet_type=IpatBetType.TANSYO,
                    number="01",
                    amount=100,
                ),
            ],
            status=PurchaseStatus.COMPLETED,
            total_amount=Money.of(100),
            created_at=datetime(2026, 2, 7, 10, 0, 0),
            updated_at=datetime(2026, 2, 7, 10, 0, 0),
        )
        order_repo.save(order)

        event = _auth_event(path_params={"purchase_id": "p-001"})
        result = get_purchase_detail_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["purchase_id"] == "p-001"

    def test_他ユーザーの注文で403(self) -> None:
        _, order_repo, _, _, _ = _setup_deps()
        order = PurchaseOrder(
            id=PurchaseId("p-002"),
            user_id=UserId("other-user"),
            cart_id=CartId("cart-001"),
            bet_lines=[],
            status=PurchaseStatus.COMPLETED,
            total_amount=Money.of(100),
            created_at=datetime(2026, 2, 7, 10, 0, 0),
            updated_at=datetime(2026, 2, 7, 10, 0, 0),
        )
        order_repo.save(order)

        event = _auth_event(path_params={"purchase_id": "p-002"})
        result = get_purchase_detail_handler(event, None)
        assert result["statusCode"] == 403

    def test_存在しない注文で404(self) -> None:
        _setup_deps()
        event = _auth_event(path_params={"purchase_id": "nonexistent"})
        result = get_purchase_detail_handler(event, None)
        assert result["statusCode"] == 404
