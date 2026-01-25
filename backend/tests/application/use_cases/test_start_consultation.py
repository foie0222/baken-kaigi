"""StartConsultationUseCaseのテスト."""
from datetime import date, datetime

import pytest

from src.domain.entities import Cart, ConsultationSession, Message
from src.domain.enums import BetType, SessionStatus
from src.domain.identifiers import CartId, RaceId, SessionId, UserId
from src.domain.ports import (
    PastRaceStats,
    AIClient,
    AmountFeedbackContext,
    BetFeedbackContext,
    CartRepository,
    ConsultationContext,
    ConsultationSessionRepository,
    HorsePerformanceData,
    JockeyInfoData,
    JockeyStatsData,
    JockeyStatsDetailData,
    PedigreeData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
    TrainingRecordData,
    TrainingSummaryData,
    WeightData,
)
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
        return [s for s in self._sessions.values() if s.user_id == user_id]

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

    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        return None

    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        return []

    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        return {}

    def get_jra_checksum(
        self,
        venue_code: str,
        kaisai_kai: str,
        kaisai_nichime: int,
        race_number: int,
    ) -> int | None:
        return None

    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        return []

    def get_past_race_stats(
        self,
        track_type: str,
        distance: int,
        grade_class: str | None = None,
        limit: int = 100
    ) -> PastRaceStats | None:
        """過去の同条件レース統計を取得する（モック実装）."""
        return None

    def get_jockey_info(self, jockey_id: str) -> JockeyInfoData | None:
        """騎手基本情報を取得する（モック実装）."""
        return None

    def get_jockey_stats_detail(
        self,
        jockey_id: str,
        year: int | None = None,
        period: str = "recent",
    ) -> JockeyStatsDetailData | None:
        """騎手成績統計を取得する（モック実装）."""
        return None

    def get_horse_performances(
        self,
        horse_id: str,
        limit: int = 5,
        track_type: str | None = None,
    ) -> list[HorsePerformanceData]:
        """馬の過去成績を取得する（モック実装）."""
        return []

    def get_horse_training(
        self,
        horse_id: str,
        limit: int = 5,
        days: int = 30,
    ) -> tuple[list[TrainingRecordData], TrainingSummaryData | None]:
        """馬の調教データを取得する（モック実装）."""
        return [], None


class MockAIClient(AIClient):
    """テスト用のモックAIクライアント."""

    def generate_bet_feedback(self, context: BetFeedbackContext) -> str:
        return f"{context.race_name}のフィードバック"

    def generate_amount_feedback(self, context: AmountFeedbackContext) -> str:
        return f"合計{context.total_amount}円のフィードバック"

    def generate_conversation_response(
        self, messages: list[Message], context: ConsultationContext
    ) -> str:
        return "AIの応答"


class TestStartConsultationUseCase:
    """StartConsultationUseCaseの単体テスト."""

    def test_カートから相談セッションを開始できる(self) -> None:
        """カートから相談セッションを開始できることを確認."""
        from src.application.use_cases.start_consultation import (
            StartConsultationUseCase,
        )

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

        use_case = StartConsultationUseCase(
            cart_repo, session_repo, race_provider, ai_client
        )
        result = use_case.execute(cart.cart_id)

        assert result.session_id is not None
        assert result.status == SessionStatus.IN_PROGRESS
        assert result.total_amount.value == 100
        assert len(result.cart_items) == 1

    def test_存在しないカートIDでエラー(self) -> None:
        """存在しないカートIDでエラーが発生することを確認."""
        from src.application.use_cases.start_consultation import (
            CartNotFoundError,
            StartConsultationUseCase,
        )

        cart_repo = MockCartRepository()
        session_repo = MockConsultationSessionRepository()
        race_provider = MockRaceDataProvider()
        ai_client = MockAIClient()

        use_case = StartConsultationUseCase(
            cart_repo, session_repo, race_provider, ai_client
        )

        with pytest.raises(CartNotFoundError):
            use_case.execute(CartId("nonexistent"))

    def test_空のカートでエラー(self) -> None:
        """空のカートでエラーが発生することを確認."""
        from src.application.use_cases.start_consultation import (
            EmptyCartError,
            StartConsultationUseCase,
        )

        cart_repo = MockCartRepository()
        session_repo = MockConsultationSessionRepository()
        race_provider = MockRaceDataProvider()
        ai_client = MockAIClient()

        cart = Cart.create()
        cart_repo.save(cart)

        use_case = StartConsultationUseCase(
            cart_repo, session_repo, race_provider, ai_client
        )

        with pytest.raises(EmptyCartError):
            use_case.execute(cart.cart_id)

    def test_フィードバックが生成される(self) -> None:
        """相談開始時にフィードバックが生成されることを確認."""
        from src.application.use_cases.start_consultation import (
            StartConsultationUseCase,
        )

        cart_repo = MockCartRepository()
        session_repo = MockConsultationSessionRepository()
        race_provider = MockRaceDataProvider()
        ai_client = MockAIClient()

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

        use_case = StartConsultationUseCase(
            cart_repo, session_repo, race_provider, ai_client
        )
        result = use_case.execute(cart.cart_id)

        assert len(result.data_feedbacks) == 1
        assert result.amount_feedback is not None
