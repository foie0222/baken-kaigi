"""カートAPIハンドラーのテスト."""
import json

import pytest

from src.api.dependencies import Dependencies
from src.domain.entities import Cart
from src.domain.enums import BetType
from src.domain.identifiers import CartId, RaceId, UserId
from src.domain.ports import CartRepository
from src.domain.value_objects import BetSelection, HorseNumbers, Money


class MockCartRepository(CartRepository):
    """テスト用のモックカートリポジトリ."""

    def __init__(self) -> None:
        self._carts: dict[str, Cart] = {}
        self._carts_by_user: dict[str, Cart] = {}

    def save(self, cart: Cart) -> None:
        self._carts[str(cart.cart_id)] = cart
        if cart.user_id:
            self._carts_by_user[str(cart.user_id)] = cart

    def find_by_id(self, cart_id: CartId) -> Cart | None:
        return self._carts.get(str(cart_id))

    def find_by_user_id(self, user_id: UserId) -> Cart | None:
        return self._carts_by_user.get(str(user_id))

    def delete(self, cart_id: CartId) -> None:
        if str(cart_id) in self._carts:
            cart = self._carts.pop(str(cart_id))
            if cart.user_id and str(cart.user_id) in self._carts_by_user:
                del self._carts_by_user[str(cart.user_id)]


@pytest.fixture(autouse=True)
def reset_dependencies():
    """各テスト前に依存性をリセット."""
    Dependencies.reset()
    yield
    Dependencies.reset()


class TestAddToCartAmountValidation:
    """POST /cart/items の金額バリデーションテスト."""

    def test_amountがfloatの場合intに変換される(self) -> None:
        """100.0 → int(100)に変換されてカートに追加される."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "WIN",
                    "horse_numbers": [1],
                    "amount": 100.0,
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["total_amount"] == 100
        assert isinstance(body["total_amount"], int)

    def test_amountが小数の場合400(self) -> None:
        """100.5 → 400 Bad Request."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "WIN",
                    "horse_numbers": [1],
                    "amount": 100.5,
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 400

    def test_amountがboolの場合400(self) -> None:
        """True → 400 Bad Request（boolはintのサブクラス）."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "WIN",
                    "horse_numbers": [1],
                    "amount": True,
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 400

    def test_amountが文字列の場合400(self) -> None:
        """文字列 → 400 Bad Request."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "WIN",
                    "horse_numbers": [1],
                    "amount": "100",
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 400

    def test_amountが0の場合400(self) -> None:
        """0 → 400 Bad Request."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "WIN",
                    "horse_numbers": [1],
                    "amount": 0,
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 400

    def test_amountが負の場合400(self) -> None:
        """-100 → 400 Bad Request."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "WIN",
                    "horse_numbers": [1],
                    "amount": -100,
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 400

    def test_amountがNaNの場合400(self) -> None:
        """NaN → 400 Bad Request（JSONパーサーがNaN非対応のため get_body で弾かれる）."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": '{"race_id":"2024060111","race_name":"日本ダービー","bet_type":"WIN","horse_numbers":[1],"amount":NaN}',
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 400

    def test_amountがInfinityの場合400(self) -> None:
        """Infinity → 400 Bad Request."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": '{"race_id":"2024060111","race_name":"日本ダービー","bet_type":"WIN","horse_numbers":[1],"amount":Infinity}',
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 400

    def test_amountが100円未満の場合400(self) -> None:
        """50 → 400 Bad Request（BetSelectionバリデーション）."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "WIN",
                    "horse_numbers": [1],
                    "amount": 50,
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 400


class TestAddToCartHandler:
    """POST /cart/items ハンドラーのテスト."""

    def test_新規カートに買い目を追加できる(self) -> None:
        """新規カートに買い目を追加できることを確認."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "WIN",
                    "horse_numbers": [1],
                    "amount": 100,
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "cart_id" in body
        assert body["item_count"] == 1
        assert body["total_amount"] == 100

    def test_既存カートに買い目を追加できる(self) -> None:
        """既存カートに買い目を追加できることを確認."""
        from src.api.handlers.cart import add_to_cart

        repository = MockCartRepository()
        cart = Cart.create()
        cart.add_item(
            race_id=RaceId("2024060101"),
            race_name="1R",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        repository.save(cart)
        Dependencies.set_cart_repository(repository)

        event = {
            "body": json.dumps(
                {
                    "cart_id": str(cart.cart_id),
                    "race_id": "2024060111",
                    "race_name": "日本ダービー",
                    "bet_type": "QUINELLA",
                    "horse_numbers": [1, 2],
                    "amount": 500,
                }
            ),
        }

        response = add_to_cart(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["cart_id"] == str(cart.cart_id)
        assert body["item_count"] == 2
        assert body["total_amount"] == 600


class TestAddToCartTypeValidation:
    """POST /cart/items の型バリデーションテスト."""

    def test_race_idが整数の場合400(self) -> None:
        from src.api.handlers.cart import add_to_cart

        Dependencies.set_cart_repository(MockCartRepository())
        event = {
            "body": json.dumps({
                "race_id": 2024060111,
                "race_name": "日本ダービー",
                "bet_type": "WIN",
                "horse_numbers": [1],
                "amount": 100,
            }),
        }
        response = add_to_cart(event, None)
        assert response["statusCode"] == 400

    def test_race_nameが整数の場合400(self) -> None:
        from src.api.handlers.cart import add_to_cart

        Dependencies.set_cart_repository(MockCartRepository())
        event = {
            "body": json.dumps({
                "race_id": "2024060111",
                "race_name": 12345,
                "bet_type": "WIN",
                "horse_numbers": [1],
                "amount": 100,
            }),
        }
        response = add_to_cart(event, None)
        assert response["statusCode"] == 400

    def test_race_idが空文字の場合400(self) -> None:
        from src.api.handlers.cart import add_to_cart

        Dependencies.set_cart_repository(MockCartRepository())
        event = {
            "body": json.dumps({
                "race_id": "",
                "race_name": "日本ダービー",
                "bet_type": "WIN",
                "horse_numbers": [1],
                "amount": 100,
            }),
        }
        response = add_to_cart(event, None)
        assert response["statusCode"] == 400

    def test_bet_typeが整数の場合400(self) -> None:
        from src.api.handlers.cart import add_to_cart

        Dependencies.set_cart_repository(MockCartRepository())
        event = {
            "body": json.dumps({
                "race_id": "2024060111",
                "race_name": "日本ダービー",
                "bet_type": 123,
                "horse_numbers": [1],
                "amount": 100,
            }),
        }
        response = add_to_cart(event, None)
        assert response["statusCode"] == 400

    def test_horse_numbersが文字列の場合400(self) -> None:
        from src.api.handlers.cart import add_to_cart

        Dependencies.set_cart_repository(MockCartRepository())
        event = {
            "body": json.dumps({
                "race_id": "2024060111",
                "race_name": "日本ダービー",
                "bet_type": "WIN",
                "horse_numbers": "1,2,3",
                "amount": 100,
            }),
        }
        response = add_to_cart(event, None)
        assert response["statusCode"] == 400

    def test_horse_numbersの要素が文字列の場合400(self) -> None:
        from src.api.handlers.cart import add_to_cart

        Dependencies.set_cart_repository(MockCartRepository())
        event = {
            "body": json.dumps({
                "race_id": "2024060111",
                "race_name": "日本ダービー",
                "bet_type": "WIN",
                "horse_numbers": ["1", "2"],
                "amount": 100,
            }),
        }
        response = add_to_cart(event, None)
        assert response["statusCode"] == 400


class TestGetCartHandler:
    """GET /cart/{cart_id} ハンドラーのテスト."""

    def test_カートを取得できる(self) -> None:
        """カートを取得できることを確認."""
        from src.api.handlers.cart import get_cart

        repository = MockCartRepository()
        cart = Cart.create()
        cart.add_item(
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        repository.save(cart)
        Dependencies.set_cart_repository(repository)

        event = {"pathParameters": {"cart_id": str(cart.cart_id)}}

        response = get_cart(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["items"]) == 1
        assert body["total_amount"] == 100

    def test_存在しないカートで404(self) -> None:
        """存在しないカートで404が返ることを確認."""
        from src.api.handlers.cart import get_cart

        repository = MockCartRepository()
        Dependencies.set_cart_repository(repository)

        event = {"pathParameters": {"cart_id": "nonexistent"}}

        response = get_cart(event, None)

        assert response["statusCode"] == 404


class TestRemoveFromCartHandler:
    """DELETE /cart/{cart_id}/items/{item_id} ハンドラーのテスト."""

    def test_アイテムを削除できる(self) -> None:
        """アイテムを削除できることを確認."""
        from src.api.handlers.cart import remove_from_cart

        repository = MockCartRepository()
        cart = Cart.create()
        item = cart.add_item(
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        repository.save(cart)
        Dependencies.set_cart_repository(repository)

        event = {
            "pathParameters": {
                "cart_id": str(cart.cart_id),
                "item_id": str(item.item_id),
            }
        }

        response = remove_from_cart(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["item_count"] == 0


class TestClearCartHandler:
    """DELETE /cart/{cart_id} ハンドラーのテスト."""

    def test_カートをクリアできる(self) -> None:
        """カートをクリアできることを確認."""
        from src.api.handlers.cart import clear_cart

        repository = MockCartRepository()
        cart = Cart.create()
        cart.add_item(
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        cart.add_item(
            race_id=RaceId("2024060101"),
            race_name="1R",
            bet_selection=BetSelection(
                bet_type=BetType.QUINELLA,
                horse_numbers=HorseNumbers([1, 2]),
                amount=Money(500),
            ),
        )
        repository.save(cart)
        Dependencies.set_cart_repository(repository)

        event = {"pathParameters": {"cart_id": str(cart.cart_id)}}

        response = clear_cart(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["item_count"] == 0
        assert body["total_amount"] == 0
