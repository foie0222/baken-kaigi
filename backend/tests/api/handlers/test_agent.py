"""エージェントAPIハンドラーのテスト."""
import json

import pytest

from src.api.dependencies import Dependencies
from src.api.handlers.agent import agent_handler, agent_review_handler
from src.infrastructure.repositories.in_memory_agent_repository import InMemoryAgentRepository
from src.infrastructure.repositories.in_memory_agent_review_repository import InMemoryAgentReviewRepository


def _make_event(
    method: str = "GET",
    path: str = "/agents/me",
    sub: str | None = "usr_001",
    body: dict | None = None,
) -> dict:
    """テスト用Lambdaイベントを生成する."""
    event: dict = {"httpMethod": method, "path": path}
    if sub is not None:
        event["requestContext"] = {"authorizer": {"claims": {"sub": sub}}}
    if body is not None:
        event["body"] = json.dumps(body)
    return event


@pytest.fixture(autouse=True)
def reset_dependencies():
    """テスト毎に依存性をリセットする."""
    Dependencies.reset()
    yield
    Dependencies.reset()


class TestCreateAgent:
    """POST /agents のテスト."""

    def test_エージェントを作成できる(self):
        event = _make_event(
            method="POST",
            path="/agents",
            body={"name": "ハヤテ"},
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 201

        body = json.loads(response["body"])
        assert body["name"] == "ハヤテ"
        assert "agent_id" in body

    def test_認証なしは401(self):
        event = _make_event(method="POST", path="/agents", sub=None, body={"name": "テスト"})
        response = agent_handler(event, None)
        assert response["statusCode"] == 401

    def test_名前なしは400(self):
        event = _make_event(method="POST", path="/agents", body={})
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_重複作成は409(self):
        event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(event, None)  # 1回目
        response = agent_handler(event, None)  # 2回目
        assert response["statusCode"] == 409


class TestGetAgent:
    """GET /agents/me のテスト."""

    def test_エージェントを取得できる(self):
        # 事前にエージェント作成
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(method="GET", path="/agents/me")
        response = agent_handler(event, None)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["name"] == "ハヤテ"

    def test_未作成は404(self):
        event = _make_event(method="GET", path="/agents/me")
        response = agent_handler(event, None)
        assert response["statusCode"] == 404

    def test_認証なしは401(self):
        event = _make_event(method="GET", path="/agents/me", sub=None)
        response = agent_handler(event, None)
        assert response["statusCode"] == 401


class TestUpdateAgent:
    """PUT /agents/me のテスト."""

    def test_好み設定を更新できる(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "selected_bet_types": ["trio", "trifecta"],
                },
            },
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["betting_preference"]["selected_bet_types"] == ["trio", "trifecta"]

    def test_未作成は404(self):
        event = _make_event(method="PUT", path="/agents/me", body={"betting_preference": {"selected_bet_types": []}})
        response = agent_handler(event, None)
        assert response["statusCode"] == 404


class TestUpdateAgentPreference:
    """PUT /agents/me 好み設定更新のテスト."""

    def test_好み設定を更新できる(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "selected_bet_types": ["trio", "trifecta"],
                },
                "custom_instructions": "三連単が好き",
            },
        )
        response = agent_handler(event, None)
        body = json.loads(response["body"])
        assert response["statusCode"] == 200
        assert body["betting_preference"]["selected_bet_types"] == ["trio", "trifecta"]
        assert body["custom_instructions"] == "三連単が好き"

    def test_GETで好み設定が含まれる(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        get_event = _make_event(method="GET", path="/agents/me")
        response = agent_handler(get_event, None)
        body = json.loads(response["body"])
        assert response["statusCode"] == 200
        assert body["betting_preference"] == {
            "selected_bet_types": [],
            "min_probability": 0.0,
            "min_ev": 0.0,
            "max_probability": None,
            "max_ev": None,
            "race_budget": 0,
        }
        assert body["custom_instructions"] is None

    def test_フィルター設定を更新できる(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "selected_bet_types": [],
                    "min_probability": 0.05,
                    "min_ev": 1.5,
                },
            },
        )
        response = agent_handler(event, None)
        body = json.loads(response["body"])
        assert response["statusCode"] == 200
        assert body["betting_preference"]["min_probability"] == 0.05
        assert body["betting_preference"]["min_ev"] == 1.5

    def test_min_probabilityが範囲外で400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "min_probability": -0.01,
                },
            },
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_min_probabilityが上限超えで400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "min_probability": 0.51,
                },
            },
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_min_evが負の値で400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "min_ev": -1.0,
                },
            },
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_min_evが上限超えで400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "min_ev": 10.5,
                },
            },
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_max_probabilityがmin_probability未満で400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "min_probability": 0.10,
                    "max_probability": 0.05,
                },
            },
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_max_evがmin_ev未満で400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "min_ev": 2.0,
                    "max_ev": 1.5,
                },
            },
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_booleanはフィルター値として拒否される(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        for field in ["min_probability", "min_ev", "max_probability", "max_ev"]:
            event = _make_event(
                method="PUT",
                path="/agents/me",
                body={"betting_preference": {field: True}},
            )
            response = agent_handler(event, None)
            assert response["statusCode"] == 400, f"{field}=True should be rejected"

    def test_custom_instructionsが201文字は400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "selected_bet_types": [],
                },
                "custom_instructions": "あ" * 201,
            },
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_race_budgetを設定できる(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={
                "betting_preference": {
                    "selected_bet_types": [],
                    "race_budget": 5000,
                },
            },
        )
        response = agent_handler(event, None)
        body = json.loads(response["body"])
        assert response["statusCode"] == 200
        assert body["betting_preference"]["race_budget"] == 5000

    def test_race_budgetが負の値で400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={"betting_preference": {"race_budget": -1}},
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_race_budgetが上限超えで400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={"betting_preference": {"race_budget": 1000001}},
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_race_budgetがbooleanで400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={"betting_preference": {"race_budget": True}},
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400

    def test_race_budgetが小数で400(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ"})
        agent_handler(create_event, None)

        event = _make_event(
            method="PUT",
            path="/agents/me",
            body={"betting_preference": {"race_budget": 1000.5}},
        )
        response = agent_handler(event, None)
        assert response["statusCode"] == 400


class TestCreateReview:
    """POST /agents/me/reviews のテスト."""

    def _setup_agent(self):
        """テスト用エージェントを作成する."""
        event = _make_event(method="POST", path="/agents", body={"name": "テスト"})
        agent_handler(event, None)

    def test_振り返りを作成できる(self):
        self._setup_agent()
        event = _make_event(
            method="POST",
            path="/agents/me/reviews",
            body={
                "race_id": "race_001",
                "race_date": "2026-02-01",
                "race_name": "東京11R",
                "bets": [
                    {"bet_type": "win", "horse_numbers": [3], "amount": 1000, "result": "hit", "payout": 3000},
                ],
            },
        )
        response = agent_review_handler(event, None)
        assert response["statusCode"] == 201

        body = json.loads(response["body"])
        assert body["race_name"] == "東京11R"
        assert body["has_win"] is True
        assert body["profit"] == 2000

    def test_認証なしは401(self):
        event = _make_event(method="POST", path="/agents/me/reviews", sub=None, body={"race_id": "r", "race_date": "2026-01-01", "race_name": "R", "bets": []})
        response = agent_review_handler(event, None)
        assert response["statusCode"] == 401

    def test_パラメータ不足は400(self):
        self._setup_agent()
        event = _make_event(method="POST", path="/agents/me/reviews", body={"race_id": "r"})
        response = agent_review_handler(event, None)
        assert response["statusCode"] == 400

    def test_エージェント未作成は404(self):
        event = _make_event(
            method="POST",
            path="/agents/me/reviews",
            body={
                "race_id": "race_001",
                "race_date": "2026-02-01",
                "race_name": "東京11R",
                "bets": [{"bet_type": "win", "horse_numbers": [3], "amount": 1000, "result": "miss", "payout": 0}],
            },
        )
        response = agent_review_handler(event, None)
        assert response["statusCode"] == 404

    def test_重複レビューは409(self):
        self._setup_agent()
        body = {
            "race_id": "race_001",
            "race_date": "2026-02-01",
            "race_name": "東京11R",
            "bets": [{"bet_type": "win", "horse_numbers": [3], "amount": 1000, "result": "hit", "payout": 3000}],
        }
        event = _make_event(method="POST", path="/agents/me/reviews", body=body)
        agent_review_handler(event, None)  # 1回目
        response = agent_review_handler(event, None)  # 2回目
        assert response["statusCode"] == 409


class TestGetReviews:
    """GET /agents/me/reviews のテスト."""

    def test_振り返り一覧を取得できる(self):
        # エージェント作成
        create_event = _make_event(method="POST", path="/agents", body={"name": "テスト"})
        agent_handler(create_event, None)

        # 振り返り作成
        review_event = _make_event(
            method="POST",
            path="/agents/me/reviews",
            body={
                "race_id": "race_001",
                "race_date": "2026-02-01",
                "race_name": "東京11R",
                "bets": [{"bet_type": "win", "horse_numbers": [3], "amount": 1000, "result": "hit", "payout": 2500}],
            },
        )
        agent_review_handler(review_event, None)

        # 一覧取得
        event = _make_event(method="GET", path="/agents/me/reviews")
        response = agent_review_handler(event, None)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert len(body["reviews"]) == 1
        assert body["reviews"][0]["race_name"] == "東京11R"

    def test_空の振り返り一覧(self):
        create_event = _make_event(method="POST", path="/agents", body={"name": "テスト"})
        agent_handler(create_event, None)

        event = _make_event(method="GET", path="/agents/me/reviews")
        response = agent_review_handler(event, None)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert len(body["reviews"]) == 0

    def test_エージェント未作成は404(self):
        event = _make_event(method="GET", path="/agents/me/reviews")
        response = agent_review_handler(event, None)
        assert response["statusCode"] == 404
