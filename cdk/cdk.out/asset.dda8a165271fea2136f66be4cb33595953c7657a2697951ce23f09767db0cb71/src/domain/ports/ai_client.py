"""AI呼び出しインターフェース（ポート）."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..entities import Message


@dataclass(frozen=True)
class BetFeedbackContext:
    """買い目フィードバック生成用のコンテキスト."""

    race_name: str
    horse_numbers: list[int]
    horse_names: list[str]
    recent_results: list[str]
    jockey_stats: list[str]
    track_suitability: list[str]
    current_odds: list[str]


@dataclass(frozen=True)
class AmountFeedbackContext:
    """掛け金フィードバック生成用のコンテキスト."""

    total_amount: int
    remaining_loss_limit: int | None
    average_amount: int | None
    is_limit_exceeded: bool


@dataclass(frozen=True)
class ConsultationContext:
    """相談会話用のコンテキスト."""

    cart_summary: str
    data_feedback_summary: str
    amount_feedback_summary: str


class AIClient(ABC):
    """AI呼び出しインターフェース（インフラ層で実装）."""

    @abstractmethod
    def generate_bet_feedback(self, context: BetFeedbackContext) -> str:
        """買い目データに基づくフィードバック文を生成する."""
        pass

    @abstractmethod
    def generate_amount_feedback(self, context: AmountFeedbackContext) -> str:
        """掛け金に関するフィードバック文を生成する."""
        pass

    @abstractmethod
    def generate_conversation_response(
        self, messages: list[Message], context: ConsultationContext
    ) -> str:
        """自由会話の応答を生成する."""
        pass
