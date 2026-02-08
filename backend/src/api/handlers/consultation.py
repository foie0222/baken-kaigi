"""AI相談API ハンドラー."""
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
    EmptyCartError,
    GetConsultationUseCase,
    SendMessageUseCase,
    SessionNotFoundError,
    SessionNotInProgressError,
    StartConsultationUseCase,
)
from src.application.use_cases.start_consultation import (
    CartNotFoundError as StartCartNotFoundError,
)
from src.domain.identifiers import CartId, SessionId


def start_consultation(event: dict, context: Any) -> dict:
    """AI相談を開始する.

    POST /consultations

    Request Body:
        cart_id: カートID

    Returns:
        セッション情報
    """
    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    if "cart_id" not in body:
        return bad_request_response("cart_id is required", event=event)

    if not isinstance(body["cart_id"], str):
        return bad_request_response("cart_id must be a string", event=event)

    # 認証ユーザーID（オプション）
    user_id = get_authenticated_user_id(event)

    # ログインユーザーの場合、残り許容負け額を取得
    remaining_loss_limit = None
    if user_id is not None:
        user_repo = Dependencies.get_user_repository()
        user = user_repo.find_by_id(user_id)
        if user is not None:
            remaining_loss_limit = user.get_remaining_loss_limit()

    # ユースケース実行
    cart_repo = Dependencies.get_cart_repository()
    session_repo = Dependencies.get_session_repository()
    race_provider = Dependencies.get_race_data_provider()
    ai_client = Dependencies.get_ai_client()

    use_case = StartConsultationUseCase(
        cart_repo, session_repo, race_provider, ai_client
    )

    try:
        result = use_case.execute(
            CartId(body["cart_id"]),
            remaining_loss_limit=remaining_loss_limit,
        )
    except StartCartNotFoundError:
        return not_found_response("Cart", event=event)
    except EmptyCartError:
        return bad_request_response("Cart is empty", event=event)

    # カートアイテムをシリアライズ
    cart_items = [
        {
            "item_id": str(item.item_id),
            "race_id": str(item.race_id),
            "race_name": item.race_name,
            "bet_type": item.bet_selection.bet_type.value,
            "horse_numbers": item.bet_selection.horse_numbers.to_list(),
            "amount": item.get_amount().value,
        }
        for item in result.cart_items
    ]

    # フィードバックをシリアライズ
    data_feedbacks = [
        {
            "cart_item_id": str(fb.cart_item_id),
            "overall_comment": fb.overall_comment,
            "horse_summaries": [
                {
                    "horse_number": hs.horse_number,
                    "horse_name": hs.horse_name,
                    "recent_results": hs.recent_results,
                    "jockey_stats": hs.jockey_stats,
                    "current_odds": hs.current_odds,
                    "popularity": hs.popularity,
                }
                for hs in fb.horse_summaries
            ],
        }
        for fb in result.data_feedbacks
    ]

    amount_feedback = None
    if result.amount_feedback:
        amount_feedback = {
            "total_amount": result.amount_feedback.total_amount.value,
            "warning_level": result.amount_feedback.warning_level.value,
            "comment": result.amount_feedback.comment,
        }

    response_data = {
        "session_id": str(result.session_id),
        "status": result.status.value,
        "cart_items": cart_items,
        "total_amount": result.total_amount.value,
        "data_feedbacks": data_feedbacks,
        "amount_feedback": amount_feedback,
    }
    if user_id:
        response_data["user_id"] = str(user_id)

    return success_response(response_data, status_code=201, event=event)


def send_message(event: dict, context: Any) -> dict:
    """メッセージを送信する.

    POST /consultations/{session_id}/messages

    Path Parameters:
        session_id: セッションID

    Request Body:
        content: メッセージ内容

    Returns:
        メッセージ情報
    """
    session_id_str = get_path_parameter(event, "session_id")
    if not session_id_str:
        return bad_request_response("session_id is required", event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    if "content" not in body:
        return bad_request_response("content is required", event=event)

    if not isinstance(body["content"], str):
        return bad_request_response("content must be a string", event=event)

    # ユースケース実行
    session_repo = Dependencies.get_session_repository()
    ai_client = Dependencies.get_ai_client()

    use_case = SendMessageUseCase(session_repo, ai_client)

    try:
        result = use_case.execute(SessionId(session_id_str), body["content"])
    except SessionNotFoundError:
        return not_found_response("Session", event=event)
    except SessionNotInProgressError:
        return bad_request_response("Session is not in progress", event=event)

    # メッセージをシリアライズ
    messages = [
        {
            "message_id": str(m.message_id),
            "type": m.type.value,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in result.messages
    ]

    return success_response(
        {
            "user_message": {
                "message_id": str(result.user_message.message_id),
                "content": result.user_message.content,
            },
            "ai_message": {
                "message_id": str(result.ai_message.message_id),
                "content": result.ai_message.content,
            },
            "messages": messages,
        },
        event=event,
    )


def get_consultation(event: dict, context: Any) -> dict:
    """相談セッションを取得する.

    GET /consultations/{session_id}

    Path Parameters:
        session_id: セッションID

    Returns:
        セッション情報
    """
    session_id_str = get_path_parameter(event, "session_id")
    if not session_id_str:
        return bad_request_response("session_id is required", event=event)

    # ユースケース実行
    session_repo = Dependencies.get_session_repository()
    use_case = GetConsultationUseCase(session_repo)
    result = use_case.execute(SessionId(session_id_str))

    if result is None:
        return not_found_response("Session", event=event)

    # カートアイテムをシリアライズ
    cart_items = [
        {
            "item_id": str(item.item_id),
            "race_id": str(item.race_id),
            "race_name": item.race_name,
            "bet_type": item.bet_selection.bet_type.value,
            "horse_numbers": item.bet_selection.horse_numbers.to_list(),
            "amount": item.get_amount().value,
        }
        for item in result.cart_items
    ]

    # メッセージをシリアライズ
    messages = [
        {
            "message_id": str(m.message_id),
            "type": m.type.value,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in result.messages
    ]

    # フィードバックをシリアライズ
    data_feedbacks = [
        {
            "cart_item_id": str(fb.cart_item_id),
            "overall_comment": fb.overall_comment,
        }
        for fb in result.data_feedbacks
    ]

    amount_feedback = None
    if result.amount_feedback:
        amount_feedback = {
            "total_amount": result.amount_feedback.total_amount.value,
            "warning_level": result.amount_feedback.warning_level.value,
            "comment": result.amount_feedback.comment,
        }

    return success_response(
        {
            "session_id": str(result.session_id),
            "status": result.status.value,
            "cart_items": cart_items,
            "messages": messages,
            "total_amount": result.total_amount.value,
            "data_feedbacks": data_feedbacks,
            "amount_feedback": amount_feedback,
            "started_at": result.started_at.isoformat(),
            "ended_at": result.ended_at.isoformat() if result.ended_at else None,
        },
        event=event,
    )
