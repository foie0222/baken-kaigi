"""AI相談APIハンドラーのテスト."""
import json
from datetime import date, datetime

import pytest

from src.api.dependencies import Dependencies
from src.domain.entities import Cart, CartItem, ConsultationSession, Message
from src.domain.enums import BetType, SessionStatus
from src.domain.identifiers import CartId, RaceId, SessionId, UserId
from src.domain.ports import (
    AIClient,
    AmountFeedbackContext,
    BetFeedbackContext,
    CartRepository,
    ConsultationContext,
    ConsultationSessionRepository,
    JockeyStatsData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
)
from src.domain.value_objects import BetSelection, HorseNumbers, Money


class MockCartRepository(CartRepository):
    """テスト用のモックカートリポジトリ."""

    def __init__(self) -> None:
        self._carts: dict[str, Cart] = {}

    def save(self, cart: Cart) -> None:
        self._carts[str(cart.cart_id)] = cart

    def find_by_id(self, cart_id: CartId) -> Cart | None:
        return self._carts.get(str(cart_id))

    def find_by_user_id(self, user_id: UserId) -> Cart | None:
        return None

    def delete(self, cart_id: CartId) -> None:
        if str(cart_id) in self._carts:
            del self._carts[str(cart_id)]


class MockConsultationSessionRepository(ConsultationSessionRepository):
    """テスト用のモックセッションリポジトリ."""

    def __init__(self) -> None:
        self._sessions: dict[str, ConsultationSession] = {}

    def save(self, session: ConsultationSession) -> None:
        self._sessions[str(session.session_id)] = session

    def find_by_id(self, session_id: SessionId) -> ConsultationSession | None:
        return self._sessions.get(str(session_id))

    def find_by_user_id(self, user_id: UserId) -> list[ConsultationSession]:
        return []

    def delete(self, session_id: SessionId) -> None:
        if str(session_id) in self._sessions:
            del self._sessions[str(session_id)]


class MockRaceDataProvider(RaceDataProvider):
    """テスト用のモックレースデータプロバイダ."""

    def __init__(self) -> None:
        self._races: dict[str, RaceData] = {}
        self._runners: dict[str, list[RunnerData]] = {}

    def add_race(self, race: RaceData) -> None:
        self._races[race.race_id] = race

    def add_runners(self, race_id: str, runners: list[RunnerData]) -> None:
        self._runners[race_id] = runners

    def get_race(self, race_id: RaceId) -> RaceData | None:
        return self._races.get(str(race_id))

    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        return []

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        return self._runners.get(str(race_id), [])

    def get_past_performance(self, horse_id: str) -> list[PerformanceData]:
        return []

    def get_jockey_stats(self, jockey_id: str, course: str) -> JockeyStatsData | None:
        return None

    def get_pedigree(self, horse_id: str):
        return None

    def get_weight_history(self, horse_id: str, limit: int = 5):
        return []

    def get_race_weights(self, race_id: RaceId):
        return {}


class MockAIClient(AIClient):
    """テスト用のモックAIクライアント."""

    def generate_bet_feedback(self, context: BetFeedbackContext) -> str:
        return "フィードバック"

    def generate_amount_feedback(self, context: AmountFeedbackContext) -> str:
        return "掛け金フィードバック"

    def generate_conversation_response(
        self, messages: list[Message], context: ConsultationContext
    ) -> str:
        return "AIの応答です。立ち止まって考えましょう。"


@pytest.fixture(autouse=True)
def reset_dependencies():
    """各テスト前に依存性をリセット."""
    Dependencies.reset()
    yield
    Dependencies.reset()


class TestStartConsultationHandler:
    """POST /consultations ハンドラーのテスト."""

    def test_相談を開始できる(self) -> None:
        """相談を開始できることを確認."""
        from src.api.handlers.consultation import start_consultation

        cart_repo = MockCartRepository()
        session_repo = MockConsultationSessionRepository()
        race_provider = MockRaceDataProvider()
        ai_client = MockAIClient()

        # カートを作成
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
        cart_repo.save(cart)

        # レース情報を追加
        race_provider.add_race(
            RaceData(
                race_id="2024060111",
                race_name="日本ダービー",
                race_number=11,
                venue="東京",
                start_time=datetime(2024, 6, 1, 15, 40),
                betting_deadline=datetime(2024, 6, 1, 15, 35),
                track_condition="良",
            )
        )
        race_provider.add_runners(
            "2024060111",
            [
                RunnerData(
                    horse_number=1,
                    horse_name="ダノンデサイル",
                    horse_id="horse1",
                    jockey_name="横山武史",
                    jockey_id="jockey1",
                    odds="3.5",
                    popularity=1,
                ),
            ],
        )

        Dependencies.set_cart_repository(cart_repo)
        Dependencies.set_session_repository(session_repo)
        Dependencies.set_race_data_provider(race_provider)
        Dependencies.set_ai_client(ai_client)

        event = {"body": json.dumps({"cart_id": str(cart.cart_id)})}

        response = start_consultation(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "session_id" in body
        assert body["status"] == "in_progress"
        assert body["total_amount"] == 100

    def test_空のカートでエラー(self) -> None:
        """空のカートでエラーになることを確認."""
        from src.api.handlers.consultation import start_consultation

        cart_repo = MockCartRepository()
        session_repo = MockConsultationSessionRepository()
        race_provider = MockRaceDataProvider()
        ai_client = MockAIClient()

        cart = Cart.create()
        cart_repo.save(cart)

        Dependencies.set_cart_repository(cart_repo)
        Dependencies.set_session_repository(session_repo)
        Dependencies.set_race_data_provider(race_provider)
        Dependencies.set_ai_client(ai_client)

        event = {"body": json.dumps({"cart_id": str(cart.cart_id)})}

        response = start_consultation(event, None)

        assert response["statusCode"] == 400


class TestSendMessageHandler:
    """POST /consultations/{session_id}/messages ハンドラーのテスト."""

    def test_メッセージを送信できる(self) -> None:
        """メッセージを送信できることを確認."""
        from src.api.handlers.consultation import send_message

        session_repo = MockConsultationSessionRepository()
        ai_client = MockAIClient()

        # セッションを作成
        session = ConsultationSession.create()
        cart_item = CartItem.create(
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        session.start([cart_item])
        session_repo.save(session)

        Dependencies.set_session_repository(session_repo)
        Dependencies.set_ai_client(ai_client)

        event = {
            "pathParameters": {"session_id": str(session.session_id)},
            "body": json.dumps({"content": "この買い目で大丈夫ですか？"}),
        }

        response = send_message(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_message"]["content"] == "この買い目で大丈夫ですか？"
        assert "ai_message" in body


class TestGetConsultationHandler:
    """GET /consultations/{session_id} ハンドラーのテスト."""

    def test_セッションを取得できる(self) -> None:
        """セッションを取得できることを確認."""
        from src.api.handlers.consultation import get_consultation

        session_repo = MockConsultationSessionRepository()

        session = ConsultationSession.create()
        cart_item = CartItem.create(
            race_id=RaceId("2024060111"),
            race_name="日本ダービー",
            bet_selection=BetSelection(
                bet_type=BetType.WIN,
                horse_numbers=HorseNumbers([1]),
                amount=Money(100),
            ),
        )
        session.start([cart_item])
        session_repo.save(session)

        Dependencies.set_session_repository(session_repo)

        event = {"pathParameters": {"session_id": str(session.session_id)}}

        response = get_consultation(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "in_progress"
        assert body["total_amount"] == 100

    def test_存在しないセッションで404(self) -> None:
        """存在しないセッションで404が返ることを確認."""
        from src.api.handlers.consultation import get_consultation

        session_repo = MockConsultationSessionRepository()
        Dependencies.set_session_repository(session_repo)

        event = {"pathParameters": {"session_id": "nonexistent"}}

        response = get_consultation(event, None)

        assert response["statusCode"] == 404
