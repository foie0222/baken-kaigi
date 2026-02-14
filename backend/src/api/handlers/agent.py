"""エージェントAPI ハンドラー."""
from typing import Any

from src.api.auth import AuthenticationError, require_authenticated_user_id
from src.api.dependencies import Dependencies
from src.api.request import get_body
from src.api.response import (
    bad_request_response,
    conflict_response,
    created_response,
    not_found_response,
    success_response,
    unauthorized_response,
)
from src.application.use_cases import (
    AgentAlreadyExistsError,
    AgentNotFoundError,
    CreateAgentReviewUseCase,
    CreateAgentUseCase,
    GetAgentUseCase,
    ReviewAlreadyExistsError,
    UpdateAgentUseCase,
)
from src.domain.identifiers import UserId


def _agent_to_dict(agent) -> dict:
    """AgentエンティティをAPIレスポンス用dictに変換する."""
    return {
        "agent_id": agent.agent_id.value,
        "user_id": agent.user_id.value,
        "name": agent.name.value,
        "base_style": agent.base_style.value,
        "performance": agent.performance.to_dict(),
        "level": agent.level,
        "win_rate": round(agent.performance.win_rate * 100, 1),
        "roi": round(agent.performance.roi * 100, 1),
        "profit": agent.performance.profit,
        "betting_preference": agent.betting_preference.to_dict(),
        "custom_instructions": agent.custom_instructions,
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat(),
    }


def agent_handler(event: dict, context: Any) -> dict:
    """エージェントAPI統合ハンドラー.

    POST /agents — エージェント作成
    GET /agents/me — 自分のエージェント取得
    PUT /agents/me — エージェント更新
    """
    method = event.get("httpMethod", "")
    path = event.get("path", "")

    if method == "POST" and path.endswith("/agents"):
        return _create_agent(event)
    elif method == "GET" and path.endswith("/agents/me"):
        return _get_agent(event)
    elif method == "PUT" and path.endswith("/agents/me"):
        return _update_agent(event)

    return bad_request_response("Unknown agent endpoint", event=event)


def _create_agent(event: dict) -> dict:
    """エージェントを作成する.

    POST /agents

    Request Body:
        name: エージェント名（1〜10文字）
        base_style: ベーススタイル (solid/longshot/data/pace)
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    name = body.get("name")
    base_style = body.get("base_style")

    if not name or not isinstance(name, str):
        return bad_request_response("name is required and must be a string", event=event)
    if not base_style or not isinstance(base_style, str):
        return bad_request_response("base_style is required and must be a string", event=event)
    if base_style not in ("solid", "longshot", "data", "pace"):
        return bad_request_response(
            "base_style must be one of: solid, longshot, data, pace", event=event
        )

    repository = Dependencies.get_agent_repository()
    use_case = CreateAgentUseCase(repository)

    try:
        result = use_case.execute(user_id, name, base_style)
    except AgentAlreadyExistsError:
        return conflict_response("Agent already exists for this user", event=event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    return created_response(_agent_to_dict(result.agent), event=event)


def _get_agent(event: dict) -> dict:
    """自分のエージェントを取得する.

    GET /agents/me
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    repository = Dependencies.get_agent_repository()
    use_case = GetAgentUseCase(repository)

    try:
        result = use_case.execute(user_id)
    except AgentNotFoundError:
        return not_found_response("Agent", event=event)

    return success_response(_agent_to_dict(result.agent), event=event)


_VALID_BET_TYPE_PREFERENCES = ("trio_focused", "exacta_focused", "quinella_focused", "wide_focused", "auto")
_VALID_TARGET_STYLES = ("honmei", "medium_longshot", "big_longshot")
_VALID_BETTING_PRIORITIES = ("hit_rate", "roi", "balanced")


def _update_agent(event: dict) -> dict:
    """エージェントを更新する.

    PUT /agents/me

    Request Body:
        base_style: 新しいスタイル (solid/longshot/data/pace) [任意]
        betting_preference: 好み設定 [任意]
        custom_instructions: 追加指示 (200文字以内) [任意]
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    base_style = body.get("base_style")
    betting_preference = body.get("betting_preference")
    custom_instructions_specified = "custom_instructions" in body
    custom_instructions = body.get("custom_instructions") if custom_instructions_specified else None

    # base_style バリデーション
    if base_style is not None:
        if not isinstance(base_style, str):
            return bad_request_response("base_style must be a string", event=event)
        if base_style not in ("solid", "longshot", "data", "pace"):
            return bad_request_response(
                "base_style must be one of: solid, longshot, data, pace", event=event
            )

    # betting_preference バリデーション
    if betting_preference is not None:
        if not isinstance(betting_preference, dict):
            return bad_request_response("betting_preference must be an object", event=event)
        btp = betting_preference.get("bet_type_preference")
        if btp is not None and btp not in _VALID_BET_TYPE_PREFERENCES:
            return bad_request_response(
                f"bet_type_preference must be one of: {', '.join(_VALID_BET_TYPE_PREFERENCES)}", event=event
            )
        ts = betting_preference.get("target_style")
        if ts is not None and ts not in _VALID_TARGET_STYLES:
            return bad_request_response(
                f"target_style must be one of: {', '.join(_VALID_TARGET_STYLES)}", event=event
            )
        bp = betting_preference.get("priority")
        if bp is not None and bp not in _VALID_BETTING_PRIORITIES:
            return bad_request_response(
                f"priority must be one of: {', '.join(_VALID_BETTING_PRIORITIES)}", event=event
            )

    # custom_instructions バリデーション
    if custom_instructions is not None:
        if not isinstance(custom_instructions, str):
            return bad_request_response("custom_instructions must be a string", event=event)
        if len(custom_instructions) > 200:
            return bad_request_response("custom_instructions must be 200 characters or less", event=event)

    # 何も更新するものがない場合
    if base_style is None and betting_preference is None and not custom_instructions_specified:
        return bad_request_response("At least one of base_style, betting_preference, or custom_instructions is required", event=event)

    repository = Dependencies.get_agent_repository()
    use_case = UpdateAgentUseCase(repository)

    kwargs: dict = {"user_id": user_id}
    if base_style is not None:
        kwargs["base_style"] = base_style
    if betting_preference is not None:
        kwargs["betting_preference"] = betting_preference
    if custom_instructions_specified:
        kwargs["custom_instructions"] = custom_instructions

    try:
        result = use_case.execute(**kwargs)
    except AgentNotFoundError:
        return not_found_response("Agent", event=event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    return success_response(_agent_to_dict(result.agent), event=event)


def agent_review_handler(event: dict, context: Any) -> dict:
    """エージェント振り返りAPI統合ハンドラー.

    GET /agents/me/reviews — 振り返り一覧取得
    POST /agents/me/reviews — 振り返り生成（Phase 1では簡易実装）
    """
    method = event.get("httpMethod", "")

    if method == "GET":
        return _get_reviews(event)
    elif method == "POST":
        return _create_review(event)

    return bad_request_response("Unknown review endpoint", event=event)


def _get_reviews(event: dict) -> dict:
    """振り返り一覧を取得する.

    GET /agents/me/reviews
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    agent_repo = Dependencies.get_agent_repository()
    review_repo = Dependencies.get_agent_review_repository()

    agent = agent_repo.find_by_user_id(UserId(user_id))
    if agent is None:
        return not_found_response("Agent", event=event)

    reviews = review_repo.find_by_agent_id(agent.agent_id)

    return success_response(
        {
            "reviews": [
                {
                    "review_id": r.review_id.value,
                    "race_id": r.race_id.value,
                    "race_date": r.race_date,
                    "race_name": r.race_name,
                    "total_invested": r.total_invested,
                    "total_return": r.total_return,
                    "profit": r.profit,
                    "has_win": r.has_win,
                    "review_text": r.review_text,
                    "learnings": r.learnings,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reviews
            ],
        },
        event=event,
    )


def _create_review(event: dict) -> dict:
    """振り返りを生成する.

    POST /agents/me/reviews

    Request Body:
        race_id: レースID
        race_date: レース日付 (YYYY-MM-DD)
        race_name: レース名
        bets: 賭け結果リスト [{bet_type, horse_numbers, amount, result, payout}]
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    race_id = body.get("race_id")
    race_date = body.get("race_date")
    race_name = body.get("race_name")
    bets = body.get("bets")

    if not race_id or not isinstance(race_id, str):
        return bad_request_response("race_id is required", event=event)
    if not race_date or not isinstance(race_date, str):
        return bad_request_response("race_date is required", event=event)
    if not race_name or not isinstance(race_name, str):
        return bad_request_response("race_name is required", event=event)
    if not bets or not isinstance(bets, list):
        return bad_request_response("bets is required and must be a list", event=event)

    agent_repo = Dependencies.get_agent_repository()
    review_repo = Dependencies.get_agent_review_repository()
    use_case = CreateAgentReviewUseCase(agent_repo, review_repo)

    try:
        result = use_case.execute(user_id, race_id, race_date, race_name, bets)
    except AgentNotFoundError:
        return not_found_response("Agent", event=event)
    except ReviewAlreadyExistsError:
        return conflict_response("Review already exists for this race", event=event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    review = result.review
    return created_response(
        {
            "review_id": review.review_id.value,
            "race_id": review.race_id.value,
            "race_name": review.race_name,
            "total_invested": review.total_invested,
            "total_return": review.total_return,
            "profit": review.profit,
            "has_win": review.has_win,
            "review_text": review.review_text,
            "learnings": review.learnings,
            "created_at": review.created_at.isoformat(),
        },
        event=event,
    )
