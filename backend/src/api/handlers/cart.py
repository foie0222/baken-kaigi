"""カートAPI ハンドラー."""
import math
from typing import Any

from src.api.auth import get_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.request import get_body, get_path_parameter
from src.api.response import (
    bad_request_response,
    not_found_response,
    success_response,
)
from src.application.use_cases import (
    AddToCartUseCase,
    CartNotFoundError,
    ClearCartUseCase,
    GetCartUseCase,
    ItemNotFoundError,
    RemoveFromCartUseCase,
)
from src.domain.enums import BetType
from src.domain.identifiers import CartId, ItemId, RaceId
from src.domain.value_objects import BetSelection, HorseNumbers, Money


def add_to_cart(event: dict, context: Any) -> dict:
    """買い目をカートに追加する.

    POST /cart/items

    Request Body:
        cart_id: カートID（オプション、新規の場合は省略）
        race_id: レースID
        race_name: レース名
        bet_type: 券種 (WIN, PLACE, QUINELLA, etc.)
        horse_numbers: 馬番リスト
        amount: 金額

    Returns:
        追加結果
    """
    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    # 必須パラメータチェック
    required = ["race_id", "race_name", "bet_type", "horse_numbers", "amount"]
    for param in required:
        if param not in body:
            return bad_request_response(f"{param} is required", event=event)

    # 文字列フィールドの型・空文字チェック
    if not isinstance(body["race_id"], str) or not body["race_id"].strip():
        return bad_request_response("race_id must be a non-empty string", event=event)
    if not isinstance(body["race_name"], str) or not body["race_name"].strip():
        return bad_request_response("race_name must be a non-empty string", event=event)

    # パラメータ変換
    cart_id = CartId(body["cart_id"]) if body.get("cart_id") else None

    try:
        # 大文字・小文字両方を受け付ける
        bet_type_str = body["bet_type"].lower()
        bet_type = BetType(bet_type_str)
    except (ValueError, AttributeError):
        return bad_request_response(f"Invalid bet_type: {body['bet_type']}", event=event)

    if not isinstance(body["horse_numbers"], list):
        return bad_request_response("horse_numbers must be a list", event=event)
    if not all(isinstance(n, int) and not isinstance(n, bool) for n in body["horse_numbers"]):
        return bad_request_response("horse_numbers must be a list of integers", event=event)

    try:
        horse_numbers = HorseNumbers.from_list(body["horse_numbers"])
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    raw_amount = body["amount"]
    if isinstance(raw_amount, bool) or not isinstance(raw_amount, (int, float)):
        return bad_request_response("amount must be a positive integer", event=event)
    if isinstance(raw_amount, float):
        if not math.isfinite(raw_amount):
            return bad_request_response("amount must be a finite number", event=event)
        if raw_amount != int(raw_amount):
            return bad_request_response("amount must be a whole number", event=event)
        raw_amount = int(raw_amount)
    if raw_amount <= 0:
        return bad_request_response("amount must be a positive integer", event=event)

    try:
        amount = Money(raw_amount)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    try:
        bet_selection = BetSelection(
            bet_type=bet_type,
            horse_numbers=horse_numbers,
            amount=amount,
        )
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    # 認証ユーザーID（オプション）
    user_id = get_authenticated_user_id(event)

    # ユースケース実行
    repository = Dependencies.get_cart_repository()
    use_case = AddToCartUseCase(repository)

    try:
        result = use_case.execute(
            cart_id=cart_id,
            race_id=RaceId(body["race_id"]),
            race_name=body["race_name"],
            bet_selection=bet_selection,
        )
    except CartNotFoundError:
        return not_found_response("Cart", event=event)

    response_data = {
        "cart_id": str(result.cart_id),
        "item_id": str(result.item_id),
        "item_count": result.item_count,
        "total_amount": result.total_amount.value,
    }
    if user_id:
        response_data["user_id"] = str(user_id)

    return success_response(response_data, status_code=201, event=event)


def get_cart(event: dict, context: Any) -> dict:
    """カートを取得する.

    GET /cart/{cart_id}

    Path Parameters:
        cart_id: カートID

    Returns:
        カート情報
    """
    cart_id_str = get_path_parameter(event, "cart_id")
    if not cart_id_str:
        return bad_request_response("cart_id is required", event=event)

    # ユースケース実行
    repository = Dependencies.get_cart_repository()
    use_case = GetCartUseCase(repository)
    result = use_case.execute(CartId(cart_id_str))

    if result is None:
        return not_found_response("Cart", event=event)

    items = [
        {
            "item_id": item.item_id,
            "race_id": item.race_id,
            "race_name": item.race_name,
            "bet_type": item.bet_type,
            "horse_numbers": item.horse_numbers,
            "amount": item.amount.value,
        }
        for item in result.items
    ]

    return success_response(
        {
            "cart_id": str(result.cart_id),
            "items": items,
            "total_amount": result.total_amount.value,
            "is_empty": result.is_empty,
        },
        event=event,
    )


def remove_from_cart(event: dict, context: Any) -> dict:
    """カートからアイテムを削除する.

    DELETE /cart/{cart_id}/items/{item_id}

    Path Parameters:
        cart_id: カートID
        item_id: アイテムID

    Returns:
        削除結果
    """
    cart_id_str = get_path_parameter(event, "cart_id")
    item_id_str = get_path_parameter(event, "item_id")

    if not cart_id_str:
        return bad_request_response("cart_id is required", event=event)
    if not item_id_str:
        return bad_request_response("item_id is required", event=event)

    # ユースケース実行
    repository = Dependencies.get_cart_repository()
    use_case = RemoveFromCartUseCase(repository)

    try:
        result = use_case.execute(CartId(cart_id_str), ItemId(item_id_str))
    except CartNotFoundError:
        return not_found_response("Cart", event=event)
    except ItemNotFoundError:
        return not_found_response("Item", event=event)

    return success_response(
        {
            "success": result.success,
            "item_count": result.item_count,
            "total_amount": result.total_amount.value,
        },
        event=event,
    )


def clear_cart(event: dict, context: Any) -> dict:
    """カートをクリアする.

    DELETE /cart/{cart_id}

    Path Parameters:
        cart_id: カートID

    Returns:
        クリア結果
    """
    cart_id_str = get_path_parameter(event, "cart_id")
    if not cart_id_str:
        return bad_request_response("cart_id is required", event=event)

    # ユースケース実行
    repository = Dependencies.get_cart_repository()
    use_case = ClearCartUseCase(repository)

    try:
        result = use_case.execute(CartId(cart_id_str))
    except CartNotFoundError:
        return not_found_response("Cart", event=event)

    return success_response(
        {
            "success": result.success,
            "item_count": result.item_count,
            "total_amount": result.total_amount.value,
        },
        event=event,
    )
