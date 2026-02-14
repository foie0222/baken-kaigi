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


    def test_race_numberがfloatの場合intに変換される(self) -> None:
        cart_repo, _, cred_provider, _, _ = _setup_deps()

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
            "race_number": 11.0,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert isinstance(body["purchase_id"], str)

    def test_race_numberが小数の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11.5,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_numberがboolの場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": True,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_numberが文字列の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": "11",
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_numberが0の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 0,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_numberが13以上の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 13,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_numberがNaNの場合400(self) -> None:
        _setup_deps()
        event = _auth_event()
        event["body"] = '{"cart_id":"cart-001","race_date":"20260207","course_code":"05","race_number":NaN}'
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_numberがInfinityの場合400(self) -> None:
        _setup_deps()
        event = _auth_event()
        event["body"] = '{"cart_id":"cart-001","race_date":"20260207","course_code":"05","race_number":Infinity}'
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_dateが整数の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": 20260207,
            "course_code": "05",
            "race_number": 11,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_course_codeが整数の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": 5,
            "race_number": 11,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_cart_idが整数の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": 12345,
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_items付きでカートがDynamoDBに存在しない場合に自動作成して購入成功(self) -> None:
        cart_repo, order_repo, cred_provider, _, _ = _setup_deps()

        # カートをDynamoDBに保存しない（フロントエンドのlocalStorageのみにある状態を再現）
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
            "cart_id": "cart-local-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
            "items": [
                {
                    "race_id": "202605051211",
                    "race_name": "東京11R",
                    "bet_type": "win",
                    "horse_numbers": [1],
                    "amount": 100,
                },
            ],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["status"] == "completed"

        # カートがDynamoDBに作成されたことを確認
        saved_cart = cart_repo.find_by_id(CartId("cart-local-001"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 1

    def test_items付きでカートがDynamoDBに既に存在する場合は上書きしない(self) -> None:
        cart_repo, order_repo, cred_provider, _, _ = _setup_deps()

        # 既存のカートをDynamoDBに保存
        cart = Cart(cart_id=CartId("cart-exist"), user_id=UserId("user-001"))
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
            "cart_id": "cart-exist",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
            "items": [
                {
                    "race_id": "202605051211",
                    "race_name": "東京11R",
                    "bet_type": "win",
                    "horse_numbers": [1],
                    "amount": 200,
                },
                {
                    "race_id": "202605051211",
                    "race_name": "東京11R",
                    "bet_type": "place",
                    "horse_numbers": [2],
                    "amount": 300,
                },
            ],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201

        # 既存のカートが上書きされていないことを確認（アイテム数1のまま）
        saved_cart = cart_repo.find_by_id(CartId("cart-exist"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 1

    def test_items無しでカートがDynamoDBに存在しない場合は404(self) -> None:
        _setup_deps()

        event = _auth_event(body={
            "cart_id": "cart-nonexistent",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 404

    def test_itemsがリストでない場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
            "items": "not-a-list",
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_items要素がオブジェクトでない場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
            "items": ["not-an-object"],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_items要素に必須フィールドが欠落の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
            "items": [{"race_id": "202605051211"}],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_items要素のbet_typeが不正な場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
            "items": [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "invalid_type",
                "horse_numbers": [1],
                "amount": 100,
            }],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_items要素のamountがboolの場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "cart_id": "cart-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
            "items": [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "win",
                "horse_numbers": [1],
                "amount": True,
            }],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400


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


class TestNagashiExpansion:
    """流し（軸→相手）形式の買い目展開テスト."""

    def test_ワイド流しが個別の買い目に展開されて購入成功(self) -> None:
        """ワイド 軸:1 → 相手:8,14 が2点に展開される."""
        cart_repo, order_repo, cred_provider, _, _ = _setup_deps()
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
            "cart_id": "cart-nagashi-001",
            "race_date": "20260207",
            "course_code": "09",
            "race_number": 11,
            "items": [
                {
                    "race_id": "202609091111",
                    "race_name": "京都11R 洛陽ステークス",
                    "bet_type": "quinella_place",
                    "horse_numbers": [1, 8, 14],
                    "amount": 6000,
                },
            ],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201

        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi-001"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 2

    def test_馬連流しが個別の買い目に展開される(self) -> None:
        """馬連 軸:3 → 相手:1,5,7 が3点に展開される."""
        cart_repo, _, cred_provider, _, _ = _setup_deps()
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
            "cart_id": "cart-nagashi-002",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 5,
            "items": [
                {
                    "race_id": "202605050505",
                    "race_name": "東京5R",
                    "bet_type": "quinella",
                    "horse_numbers": [3, 1, 5, 7],
                    "amount": 3000,
                },
            ],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201

        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi-002"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 3

    def test_通常の2頭ワイドは展開されない(self) -> None:
        """通常選択の2頭ワイドはそのまま1点."""
        cart_repo, _, cred_provider, _, _ = _setup_deps()
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
            "cart_id": "cart-normal-001",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 1,
            "items": [
                {
                    "race_id": "202605050101",
                    "race_name": "東京1R",
                    "bet_type": "quinella_place",
                    "horse_numbers": [1, 8],
                    "amount": 1000,
                },
            ],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201

        saved_cart = cart_repo.find_by_id(CartId("cart-normal-001"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 1

    def test_流しで1点あたり金額が100円未満の場合はエラー(self) -> None:
        """300円を4点に分割 → 75円/点でエラー."""
        _, _, cred_provider, _, _ = _setup_deps()
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
            "cart_id": "cart-nagashi-small",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 6,
            "items": [
                {
                    "race_id": "202605050606",
                    "race_name": "東京6R",
                    "bet_type": "quinella",
                    "horse_numbers": [3, 1, 5, 7, 9],
                    "amount": 300,
                },
            ],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_流しで金額が点数で割り切れない場合はエラー(self) -> None:
        """6100円を3点に分割 → 割り切れずエラー."""
        _, _, cred_provider, _, _ = _setup_deps()
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
            "cart_id": "cart-nagashi-remainder",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 7,
            "items": [
                {
                    "race_id": "202605050707",
                    "race_name": "東京7R",
                    "bet_type": "quinella",
                    "horse_numbers": [4, 1, 5, 7],
                    "amount": 6100,
                },
            ],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_三連複の流し形式はエラー(self) -> None:
        """三連複の流しは未サポートでエラー."""
        _, _, cred_provider, _, _ = _setup_deps()
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
            "cart_id": "cart-nagashi-trio",
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 8,
            "items": [
                {
                    "race_id": "202605050808",
                    "race_name": "東京8R",
                    "bet_type": "trio",
                    "horse_numbers": [3, 1, 5, 7],
                    "amount": 1200,
                },
            ],
        })
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400


class TestExpandBet:
    """_expand_bet による各種買い方展開のE2Eテスト."""

    def _make_event(self, items: list[dict], cart_id: str = "cart-expand") -> dict:
        """テスト用イベントを生成する."""
        return _auth_event(body={
            "cart_id": cart_id,
            "race_date": "20260207",
            "course_code": "05",
            "race_number": 11,
            "items": items,
        })

    def _setup_and_get_creds(self):
        """依存関係セットアップとクレデンシャル登録."""
        cart_repo, order_repo, cred_provider, gateway, spending = _setup_deps()
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            ),
        )
        return cart_repo

    def test_馬連BOX_3頭が3点に展開される(self) -> None:
        """quinella box [1,2,3] → C(3,2)=3点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "quinella",
                "horse_numbers": [1, 2, 3],
                "amount": 300,
                "bet_method": "box",
                "bet_count": 3,
                "column_selections": {"col1": [1, 2, 3], "col2": [], "col3": []},
            }],
            cart_id="cart-box-quinella",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-box-quinella"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 3

    def test_馬単BOX_2頭が2点に展開される(self) -> None:
        """exacta box [1,2] → P(2,2)=2点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "exacta",
                "horse_numbers": [1, 2],
                "amount": 200,
                "bet_method": "box",
                "bet_count": 2,
                "column_selections": {"col1": [1, 2], "col2": [], "col3": []},
            }],
            cart_id="cart-box-exacta-2",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-box-exacta-2"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 2

    def test_馬単BOX_3頭が6点に展開される(self) -> None:
        """exacta box [1,2,3] → P(3,2)=6点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "exacta",
                "horse_numbers": [1, 2, 3],
                "amount": 600,
                "bet_method": "box",
                "bet_count": 6,
                "column_selections": {"col1": [1, 2, 3], "col2": [], "col3": []},
            }],
            cart_id="cart-box-exacta-3",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-box-exacta-3"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 6

    def test_三連複BOX_4頭が4点に展開される(self) -> None:
        """trio box [1,2,3,4] → C(4,3)=4点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "trio",
                "horse_numbers": [1, 2, 3, 4],
                "amount": 400,
                "bet_method": "box",
                "bet_count": 4,
                "column_selections": {"col1": [1, 2, 3, 4], "col2": [], "col3": []},
            }],
            cart_id="cart-box-trio",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-box-trio"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 4

    def test_三連単BOX_3頭が6点に展開される(self) -> None:
        """trifecta box [1,2,3] → P(3,3)=6点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "trifecta",
                "horse_numbers": [1, 2, 3],
                "amount": 600,
                "bet_method": "box",
                "bet_count": 6,
                "column_selections": {"col1": [1, 2, 3], "col2": [], "col3": []},
            }],
            cart_id="cart-box-trifecta",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-box-trifecta"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 6

    def test_馬単1着流しが正しい順序で展開される(self) -> None:
        """exacta nagashi_1, axis=3, partners=[1,5] → (3,1),(3,5)."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "exacta",
                "horse_numbers": [3, 1, 5],
                "amount": 200,
                "bet_method": "nagashi_1",
                "bet_count": 2,
                "column_selections": {"col1": [3], "col2": [1, 5], "col3": []},
            }],
            cart_id="cart-nagashi1-exacta",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi1-exacta"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 2

    def test_馬単2着流しが正しい順序で展開される(self) -> None:
        """exacta nagashi_2, axis=5, partners=[1,3] → (1,5),(3,5)."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "exacta",
                "horse_numbers": [5, 1, 3],
                "amount": 200,
                "bet_method": "nagashi_2",
                "bet_count": 2,
                "column_selections": {"col1": [5], "col2": [1, 3], "col3": []},
            }],
            cart_id="cart-nagashi2-exacta",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi2-exacta"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 2

    def test_馬単マルチが両方向に展開される(self) -> None:
        """exacta nagashi_multi, axis=3, partners=[1,5] → 4点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "exacta",
                "horse_numbers": [3, 1, 5],
                "amount": 400,
                "bet_method": "nagashi_multi",
                "bet_count": 4,
                "column_selections": {"col1": [3], "col2": [1, 5], "col3": []},
            }],
            cart_id="cart-multi-exacta",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-multi-exacta"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 4

    def test_三連複軸1頭流しが展開される(self) -> None:
        """trio nagashi, axis=1, partners=[3,5,7] → C(3,2)=3点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "trio",
                "horse_numbers": [1, 3, 5, 7],
                "amount": 300,
                "bet_method": "nagashi",
                "bet_count": 3,
                "column_selections": {"col1": [1], "col2": [3, 5, 7], "col3": []},
            }],
            cart_id="cart-nagashi-trio-1axis",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi-trio-1axis"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 3

    def test_三連単1着流しが展開される(self) -> None:
        """trifecta nagashi_1, axis=1, partners=[3,5] → P(2,2)=2点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "trifecta",
                "horse_numbers": [1, 3, 5],
                "amount": 200,
                "bet_method": "nagashi_1",
                "bet_count": 2,
                "column_selections": {"col1": [1], "col2": [3, 5], "col3": []},
            }],
            cart_id="cart-nagashi1-trifecta",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi1-trifecta"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 2

    def test_三連複軸2頭流しが展開される(self) -> None:
        """trio nagashi_2, axes=[1,3], partners=[5,7] → 2点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "trio",
                "horse_numbers": [1, 3, 5, 7],
                "amount": 200,
                "bet_method": "nagashi_2",
                "bet_count": 2,
                "column_selections": {"col1": [1, 3], "col2": [5, 7], "col3": []},
            }],
            cart_id="cart-nagashi2-trio",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi2-trio"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 2

    def test_三連単2着流しが展開される(self) -> None:
        """trifecta nagashi_2, axis=5, partners=[1,3] → P(2,2)=2点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "trifecta",
                "horse_numbers": [5, 1, 3],
                "amount": 200,
                "bet_method": "nagashi_2",
                "bet_count": 2,
                "column_selections": {"col1": [5], "col2": [1, 3], "col3": []},
            }],
            cart_id="cart-nagashi2-trifecta",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi2-trifecta"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 2

    def test_三連単軸2頭12着流しが展開される(self) -> None:
        """trifecta nagashi_12, col1=[1], col3=[3], col2=[5,7] → 2点."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "trifecta",
                "horse_numbers": [1, 3, 5, 7],
                "amount": 200,
                "bet_method": "nagashi_12",
                "bet_count": 2,
                "column_selections": {"col1": [1], "col2": [5, 7], "col3": [3]},
            }],
            cart_id="cart-nagashi12-trifecta",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-nagashi12-trifecta"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 2

    def test_馬連フォーメーションが展開される(self) -> None:
        """quinella formation, col1=[1,3], col2=[5,7] → unique sorted pairs."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "quinella",
                "horse_numbers": [1, 3, 5, 7],
                "amount": 400,
                "bet_method": "formation",
                "bet_count": 4,
                "column_selections": {"col1": [1, 3], "col2": [5, 7], "col3": []},
            }],
            cart_id="cart-form-quinella",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-form-quinella"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 4

    def test_馬単フォーメーションが展開される(self) -> None:
        """exacta formation, col1=[1,3], col2=[5,7] → ordered pairs (no self)."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "exacta",
                "horse_numbers": [1, 3, 5, 7],
                "amount": 400,
                "bet_method": "formation",
                "bet_count": 4,
                "column_selections": {"col1": [1, 3], "col2": [5, 7], "col3": []},
            }],
            cart_id="cart-form-exacta",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-form-exacta"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 4

    def test_三連複フォーメーションが展開される(self) -> None:
        """trio formation, col1=[1,2], col2=[3,4], col3=[5,6] → unique sorted triples."""
        cart_repo = self._setup_and_get_creds()
        # col1=[1,2], col2=[3,4], col3=[5,6] → all different, so 2*2*2=8 unique triples
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "trio",
                "horse_numbers": [1, 2, 3, 4, 5, 6],
                "amount": 800,
                "bet_method": "formation",
                "bet_count": 8,
                "column_selections": {"col1": [1, 2], "col2": [3, 4], "col3": [5, 6]},
            }],
            cart_id="cart-form-trio",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-form-trio"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 8

    def test_bet_method未指定でも後方互換性がある(self) -> None:
        """old format (no bet_method) still works for normal bets."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "win",
                "horse_numbers": [1],
                "amount": 100,
            }],
            cart_id="cart-compat",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-compat"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 1

    def test_1点あたり金額が100円未満でエラー(self) -> None:
        """200円を3点に分割 → 66円/点でエラー."""
        self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "quinella",
                "horse_numbers": [1, 2, 3],
                "amount": 200,
                "bet_method": "box",
                "bet_count": 3,
                "column_selections": {"col1": [1, 2, 3], "col2": [], "col3": []},
            }],
            cart_id="cart-amount-error",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 400

    def test_通常買いはbet_method指定でそのまま1点(self) -> None:
        """normal with bet_method="normal" → 1 bet."""
        cart_repo = self._setup_and_get_creds()
        event = self._make_event(
            [{
                "race_id": "202605051211",
                "race_name": "東京11R",
                "bet_type": "quinella",
                "horse_numbers": [1, 3],
                "amount": 100,
                "bet_method": "normal",
                "column_selections": {"col1": [1], "col2": [3], "col3": []},
            }],
            cart_id="cart-normal-explicit",
        )
        result = submit_purchase_handler(event, None)
        assert result["statusCode"] == 201
        saved_cart = cart_repo.find_by_id(CartId("cart-normal-explicit"))
        assert saved_cart is not None
        assert saved_cart.get_item_count() == 1
