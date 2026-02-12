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
    CreateAgentUseCase,
    GetAgentUseCase,
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
        "stats": agent.stats.to_dict(),
        "performance": agent.performance.to_dict(),
        "level": agent.level,
        "win_rate": round(agent.performance.win_rate * 100, 1),
        "roi": round(agent.performance.roi * 100, 1),
        "profit": agent.performance.profit,
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


def _update_agent(event: dict) -> dict:
    """エージェントを更新する.

    PUT /agents/me

    Request Body:
        name: 新しいエージェント名（オプション）
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

    if name is not None and not isinstance(name, str):
        return bad_request_response("name must be a string", event=event)
    if name is None:
        return bad_request_response("At least name is required for update", event=event)

    repository = Dependencies.get_agent_repository()
    use_case = UpdateAgentUseCase(repository)

    try:
        result = use_case.execute(user_id, name=name)
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
                    "stats_change": r.stats_change,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reviews
            ],
        },
        event=event,
    )


def _create_review(event: dict) -> dict:
    """振り返りを生成する（Phase 1ではプレースホルダー）.

    POST /agents/me/reviews
    """
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    # Phase 1では振り返り生成のバックエンドロジックは後から実装
    return success_response(
        {"message": "Review generation will be implemented in Phase 1 Step 6"},
        event=event,
    )
