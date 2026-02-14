"""購入APIハンドラー."""
import logging
import math
from datetime import datetime, timezone
from itertools import combinations, permutations
from typing import Any

logger = logging.getLogger(__name__)

MIN_RACE_NUMBER = 1
MAX_RACE_NUMBER = 12

from src.api.auth import AuthenticationError, require_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.request import get_body, get_path_parameter
from src.api.response import (
    bad_request_response,
    forbidden_response,
    internal_error_response,
    not_found_response,
    success_response,
    unauthorized_response,
)
from src.application.use_cases.get_purchase_history import GetPurchaseHistoryUseCase
from src.application.use_cases.submit_purchase import (
    CartNotFoundError,
    CredentialsNotFoundError,
    IpatSubmissionError,
    PurchaseValidationError,
    SubmitPurchaseUseCase,
)
from src.domain.entities import Cart
from src.domain.enums import BetType
from src.domain.identifiers import CartId, PurchaseId, RaceId, UserId
from src.domain.ports import IpatGatewayError
from src.domain.value_objects import BetSelection, HorseNumbers, Money


def _validate_per_amount(total_amount: int, bet_count: int) -> int:
    """1点あたりの金額を計算しバリデーションする."""
    if total_amount % bet_count != 0:
        raise ValueError(
            "合計金額を均等に分割できません。"
            "1点あたりの金額が整数になるように入力してください。"
        )

    per_amount = total_amount // bet_count

    if per_amount < 100 or per_amount % 100 != 0:
        raise ValueError(
            "1点あたり金額が不正です。"
            "1点あたり100円以上かつ100円単位になるように入力してください。"
        )

    return per_amount


def _expand_box(col1: list[int], bet_type: BetType) -> list[tuple[int, ...]]:
    """BOX展開: col1からrequired_count頭の組み合わせ/順列を生成する."""
    required = bet_type.get_required_count()
    if bet_type.is_order_required():
        return list(permutations(col1, required))
    else:
        return [tuple(sorted(c)) for c in combinations(col1, required)]


def _expand_formation(
    col1: list[int],
    col2: list[int],
    col3: list[int],
    bet_type: BetType,
) -> list[tuple[int, ...]]:
    """フォーメーション展開: 各列のクロス積から重複を除外して生成する."""
    required = bet_type.get_required_count()
    ordered = bet_type.is_order_required()
    results: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()

    if required == 2:
        for h1 in col1:
            for h2 in col2:
                if h1 == h2:
                    continue
                key = (h1, h2) if ordered else tuple(sorted((h1, h2)))
                if key not in seen:
                    seen.add(key)
                    results.append(key)
    elif required == 3:
        for h1 in col1:
            for h2 in col2:
                for h3 in col3:
                    if h1 == h2 or h1 == h3 or h2 == h3:
                        continue
                    key = (h1, h2, h3) if ordered else tuple(sorted((h1, h2, h3)))
                    if key not in seen:
                        seen.add(key)
                        results.append(key)

    return results


def _expand_nagashi_2horse(
    col1: list[int],
    col2: list[int],
    bet_method: str,
    bet_type: BetType,
) -> list[tuple[int, ...]]:
    """2頭式券種の流し展開."""
    axis = col1[0]
    ordered = bet_type.is_order_required()

    if bet_method in ("nagashi", "nagashi_1"):
        if ordered:
            return [(axis, p) for p in col2 if p != axis]
        else:
            return [tuple(sorted((axis, p))) for p in col2 if p != axis]
    elif bet_method == "nagashi_2":
        # 2着固定 (ordered only)
        return [(p, axis) for p in col2 if p != axis]
    elif bet_method == "nagashi_multi":
        # マルチ (ordered only): 両方向
        results: list[tuple[int, ...]] = []
        for p in col2:
            if p == axis:
                continue
            results.append((axis, p))
            results.append((p, axis))
        return results
    else:
        raise ValueError(f"未対応の流し方式です: {bet_method}")


def _expand_nagashi_3horse(
    col1: list[int],
    col2: list[int],
    col3: list[int],
    bet_method: str,
    bet_type: BetType,
) -> list[tuple[int, ...]]:
    """3頭式券種の流し展開."""
    ordered = bet_type.is_order_required()

    if bet_method == "nagashi":
        # 三連複: 軸1頭流し
        axis = col1[0]
        return [
            tuple(sorted((axis, p1, p2)))
            for p1, p2 in combinations(col2, 2)
            if axis != p1 and axis != p2
        ]
    elif bet_method == "nagashi_1":
        # 三連単: 1着固定
        axis = col1[0]
        return [
            (axis, p1, p2)
            for p1, p2 in permutations(col2, 2)
            if axis != p1 and axis != p2
        ]
    elif bet_method == "nagashi_2":
        if not ordered:
            # 三連複: 軸2頭流し col1=[a1,a2], col2=相手
            a1, a2 = col1[0], col1[1]
            return [
                tuple(sorted((a1, a2, p)))
                for p in col2
                if p != a1 and p != a2
            ]
        else:
            # 三連単: 2着固定
            axis = col1[0]
            return [
                (p1, axis, p2)
                for p1, p2 in permutations(col2, 2)
                if axis != p1 and axis != p2 and p1 != p2
            ]
    elif bet_method == "nagashi_3":
        # 三連単: 3着固定
        axis = col1[0]
        return [
            (p1, p2, axis)
            for p1, p2 in permutations(col2, 2)
            if axis != p1 and axis != p2 and p1 != p2
        ]
    elif bet_method == "nagashi_1_multi":
        # 三連単: 1着軸マルチ
        axis = col1[0]
        results: list[tuple[int, ...]] = []
        for p1, p2 in permutations(col2, 2):
            if axis == p1 or axis == p2:
                continue
            results.append((axis, p1, p2))
            results.append((p1, axis, p2))
            results.append((p1, p2, axis))
        return results
    elif bet_method == "nagashi_2_multi":
        # 三連単: 軸2頭マルチ col1=[a1,a2], col2=相手
        a1, a2 = col1[0], col1[1]
        results_list: list[tuple[int, ...]] = []
        for p in col2:
            if p == a1 or p == a2:
                continue
            for perm in permutations((a1, a2, p)):
                results_list.append(perm)
        return results_list
    elif bet_method == "nagashi_12":
        # 三連単: 1着2着固定 col1[0]=1着, col3[0]=2着, col2=3着候補
        a1 = col1[0]
        a2 = col3[0]
        return [
            (a1, a2, p) for p in col2
            if p != a1 and p != a2
        ]
    elif bet_method == "nagashi_13":
        # 三連単: 1着3着固定 col1[0]=1着, col3[0]=3着, col2=2着候補
        a1 = col1[0]
        a3 = col3[0]
        return [
            (a1, p, a3) for p in col2
            if p != a1 and p != a3
        ]
    elif bet_method == "nagashi_23":
        # 三連単: 2着3着固定 col1[0]=2着, col3[0]=3着, col2=1着候補
        a2 = col1[0]
        a3 = col3[0]
        return [
            (p, a2, a3) for p in col2
            if p != a2 and p != a3
        ]
    else:
        raise ValueError(f"未対応の流し方式です: {bet_method}")


def _expand_bet(item: dict) -> list[BetSelection]:
    """買い目を展開する.

    bet_methodとcolumn_selectionsに基づいて、BOX・流し・フォーメーション・
    マルチなどの形式を個別のBetSelectionに展開する。
    bet_methodが未指定またはnormalの場合は、後方互換のためレガシー動作を維持する。
    """
    bet_type: BetType = item["bet_type"]
    horse_numbers: list[int] = item["horse_numbers"]
    amount: int = item["amount"]
    bet_method: str = item.get("bet_method", "normal")
    column_selections: dict | None = item.get("column_selections")
    bet_count: int | None = item.get("bet_count")
    required = bet_type.get_required_count()

    # --- 後方互換: bet_method未指定 or "normal" かつ column_selections無し ---
    if (bet_method == "normal" or bet_method is None) and column_selections is None:
        if len(horse_numbers) <= required:
            return [
                BetSelection(
                    bet_type=bet_type,
                    horse_numbers=HorseNumbers.from_list(horse_numbers),
                    amount=Money(amount),
                )
            ]

        # レガシー流し: 2頭式のみ対応
        if required != 2:
            raise ValueError(
                f"{bet_type.get_display_name()}の流し形式は現在サポートされていません"
            )

        axis = horse_numbers[0]
        partners = horse_numbers[1:]
        partner_count = len(partners)
        per_amount = _validate_per_amount(amount, partner_count)

        return [
            BetSelection(
                bet_type=bet_type,
                horse_numbers=HorseNumbers.from_list([axis, partner]),
                amount=Money(per_amount),
            )
            for partner in partners
        ]

    # --- 通常買い（bet_method=normal, column_selections有り）---
    if bet_method == "normal":
        return [
            BetSelection(
                bet_type=bet_type,
                horse_numbers=HorseNumbers.from_list(horse_numbers),
                amount=Money(amount),
            )
        ]

    # --- column_selectionsが必要な方式 ---
    if column_selections is None:
        raise ValueError("column_selectionsが必要です")

    col1: list[int] = column_selections.get("col1", [])
    col2: list[int] = column_selections.get("col2", [])
    col3: list[int] = column_selections.get("col3", [])

    # 展開ロジック
    if bet_method == "box":
        expanded = _expand_box(col1, bet_type)
    elif bet_method == "formation":
        expanded = _expand_formation(col1, col2, col3, bet_type)
    elif bet_method.startswith("nagashi"):
        if required == 2:
            expanded = _expand_nagashi_2horse(col1, col2, bet_method, bet_type)
        else:
            expanded = _expand_nagashi_3horse(col1, col2, col3, bet_method, bet_type)
    else:
        raise ValueError(f"未対応の購入方式です: {bet_method}")

    if not expanded:
        raise ValueError("展開結果が0点です。選択内容を確認してください。")

    actual_count = len(expanded)
    if bet_count is not None and bet_count != actual_count:
        raise ValueError(
            f"展開点数の不一致: フロント={bet_count}点, バックエンド={actual_count}点"
        )

    per_amount = _validate_per_amount(amount, actual_count)

    return [
        BetSelection(
            bet_type=bet_type,
            horse_numbers=HorseNumbers.from_list(list(nums)),
            amount=Money(per_amount),
        )
        for nums in expanded
    ]


def submit_purchase_handler(event: dict, context: Any) -> dict:
    """購入を実行する.

    POST /purchases
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    cart_id = body.get("cart_id")
    race_date = body.get("race_date")
    course_code = body.get("course_code")
    race_number = body.get("race_number")

    if not cart_id:
        return bad_request_response("cart_id is required", event=event)
    if not isinstance(cart_id, str):
        return bad_request_response("cart_id must be a string", event=event)
    if not race_date:
        return bad_request_response("race_date is required", event=event)
    if not isinstance(race_date, str):
        return bad_request_response("race_date must be a string", event=event)
    if not course_code:
        return bad_request_response("course_code is required", event=event)
    if not isinstance(course_code, str):
        return bad_request_response("course_code must be a string", event=event)
    if race_number is None:
        return bad_request_response("race_number is required", event=event)
    if isinstance(race_number, bool) or not isinstance(race_number, (int, float)):
        return bad_request_response(
            f"race_number must be an integer between {MIN_RACE_NUMBER} and {MAX_RACE_NUMBER}",
            event=event,
        )
    if isinstance(race_number, float):
        if not math.isfinite(race_number):
            return bad_request_response("race_number must be a finite number", event=event)
        if race_number != int(race_number):
            return bad_request_response("race_number must be a whole number", event=event)
        race_number = int(race_number)
    if race_number < MIN_RACE_NUMBER or race_number > MAX_RACE_NUMBER:
        return bad_request_response(
            f"race_number must be between {MIN_RACE_NUMBER} and {MAX_RACE_NUMBER}",
            event=event,
        )

    # フロントエンドから送信されたカートアイテムのバリデーションとDynamoDB同期
    items = body.get("items")
    if items is None:
        items = []
    elif not isinstance(items, list):
        return bad_request_response("items must be a list", event=event)

    normalized_items: list[dict[str, Any]] = []
    for index, item_data in enumerate(items):
        if not isinstance(item_data, dict):
            return bad_request_response(f"items[{index}] must be an object", event=event)

        try:
            race_id_raw = item_data["race_id"]
            race_name_raw = item_data["race_name"]
            bet_type_raw = item_data["bet_type"]
            horse_numbers_raw = item_data["horse_numbers"]
            amount_raw = item_data["amount"]
        except KeyError as e:
            return bad_request_response(
                f"items[{index}] is missing required field '{e.args[0]}'",
                event=event,
            )

        if not isinstance(race_id_raw, str):
            return bad_request_response(f"items[{index}].race_id must be a string", event=event)
        if not isinstance(race_name_raw, str):
            return bad_request_response(f"items[{index}].race_name must be a string", event=event)
        if not isinstance(bet_type_raw, str):
            return bad_request_response(f"items[{index}].bet_type must be a string", event=event)

        try:
            bet_type = BetType(bet_type_raw.lower())
        except ValueError:
            return bad_request_response(f"items[{index}].bet_type is invalid", event=event)

        if not isinstance(horse_numbers_raw, list):
            return bad_request_response(f"items[{index}].horse_numbers must be a list", event=event)
        try:
            horse_numbers_list = [int(n) for n in horse_numbers_raw]
        except (TypeError, ValueError):
            return bad_request_response(
                f"items[{index}].horse_numbers must be a list of integers",
                event=event,
            )

        if isinstance(amount_raw, bool) or not isinstance(amount_raw, (int, float)):
            return bad_request_response(f"items[{index}].amount must be a number", event=event)
        if isinstance(amount_raw, float):
            if not math.isfinite(amount_raw):
                return bad_request_response(f"items[{index}].amount must be a finite number", event=event)
            if amount_raw != int(amount_raw):
                return bad_request_response(f"items[{index}].amount must be a whole number", event=event)
            amount_value = int(amount_raw)
        else:
            amount_value = int(amount_raw)

        # オプショナルフィールド: bet_method, bet_count, column_selections
        bet_method_raw = item_data.get("bet_method", "normal")
        if not isinstance(bet_method_raw, str):
            return bad_request_response(
                f"items[{index}].bet_method must be a string", event=event
            )

        bet_count_raw = item_data.get("bet_count")
        bet_count_value: int | None = None
        if bet_count_raw is not None:
            if isinstance(bet_count_raw, bool) or not isinstance(bet_count_raw, (int, float)):
                return bad_request_response(
                    f"items[{index}].bet_count must be a number", event=event
                )
            bet_count_value = int(bet_count_raw)

        column_selections_raw = item_data.get("column_selections")
        column_selections_value: dict[str, list[int]] | None = None
        if column_selections_raw is not None:
            if not isinstance(column_selections_raw, dict):
                return bad_request_response(
                    f"items[{index}].column_selections must be an object", event=event
                )
            column_selections_value = {
                "col1": [int(n) for n in column_selections_raw.get("col1", [])],
                "col2": [int(n) for n in column_selections_raw.get("col2", [])],
                "col3": [int(n) for n in column_selections_raw.get("col3", [])],
            }

        normalized_items.append({
            "race_id": race_id_raw,
            "race_name": race_name_raw,
            "bet_type": bet_type,
            "horse_numbers": horse_numbers_list,
            "amount": amount_value,
            "bet_method": bet_method_raw,
            "bet_count": bet_count_value,
            "column_selections": column_selections_value,
        })

    cart_repository = Dependencies.get_cart_repository()
    if normalized_items and cart_repository.find_by_id(CartId(cart_id)) is None:
        now = datetime.now(timezone.utc)
        cart = Cart(
            cart_id=CartId(cart_id),
            user_id=UserId(user_id.value),
            created_at=now,
            updated_at=now,
        )
        try:
            for item in normalized_items:
                expanded = _expand_bet(item)
                for sel in expanded:
                    cart.add_item(
                        race_id=RaceId(item["race_id"]),
                        race_name=item["race_name"],
                        bet_selection=sel,
                    )
        except ValueError as e:
            return bad_request_response(str(e), event=event)
        cart_repository.save(cart)

    use_case = SubmitPurchaseUseCase(
        cart_repository=cart_repository,
        purchase_order_repository=Dependencies.get_purchase_order_repository(),
        ipat_gateway=Dependencies.get_ipat_gateway(),
        credentials_provider=Dependencies.get_credentials_provider(),
        spending_limit_provider=Dependencies.get_spending_limit_provider(),
    )

    try:
        order = use_case.execute(
            user_id=user_id.value,
            cart_id=cart_id,
            race_date=race_date,
            course_code=course_code,
            race_number=race_number,
        )
    except CartNotFoundError:
        return not_found_response("Cart", event=event)
    except CredentialsNotFoundError:
        return bad_request_response("IPAT credentials not configured", event=event)
    except PurchaseValidationError as e:
        return bad_request_response(str(e), event=event)
    except IpatSubmissionError as e:
        logger.exception("IpatSubmissionError: %s", e)
        return internal_error_response(str(e), event=event)
    except IpatGatewayError as e:
        logger.exception("IpatGatewayError: %s", e)
        return internal_error_response("IPAT通信エラーが発生しました", event=event)

    return success_response(
        {
            "purchase_id": str(order.id.value),
            "status": order.status.value,
            "total_amount": order.total_amount.value,
            "created_at": order.created_at.isoformat(),
        },
        status_code=201,
        event=event,
    )


def get_purchase_history_handler(event: dict, context: Any) -> dict:
    """購入履歴を取得する.

    GET /purchases
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    use_case = GetPurchaseHistoryUseCase(
        purchase_order_repository=Dependencies.get_purchase_order_repository(),
    )
    orders = use_case.execute(user_id.value)

    return success_response([
        {
            "purchase_id": str(order.id.value),
            "status": order.status.value,
            "total_amount": order.total_amount.value,
            "bet_line_count": len(order.bet_lines),
            "error_message": order.error_message,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        }
        for order in orders
    ], event=event)


def get_purchase_detail_handler(event: dict, context: Any) -> dict:
    """購入詳細を取得する.

    GET /purchases/{purchase_id}
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    purchase_id_str = get_path_parameter(event, "purchase_id")
    if not purchase_id_str:
        return bad_request_response("purchase_id is required", event=event)

    repo = Dependencies.get_purchase_order_repository()
    order = repo.find_by_id(PurchaseId(purchase_id_str))

    if order is None:
        return not_found_response("Purchase order", event=event)

    if order.user_id != user_id:
        return forbidden_response(event=event)

    return success_response({
        "purchase_id": str(order.id.value),
        "user_id": str(order.user_id.value),
        "cart_id": str(order.cart_id.value),
        "status": order.status.value,
        "total_amount": order.total_amount.value,
        "bet_lines": [
            {
                "opdt": line.opdt,
                "venue_code": line.venue_code.value,
                "race_number": line.race_number,
                "bet_type": line.bet_type.value,
                "number": line.number,
                "amount": line.amount,
            }
            for line in order.bet_lines
        ],
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "error_message": order.error_message,
    }, event=event)
