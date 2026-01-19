"""フィードバック生成サービス."""
from datetime import datetime

from ..entities import CartItem
from ..ports import AIClient, BetFeedbackContext, RaceDataProvider
from ..value_objects import AmountFeedback, DataFeedback, HorseDataSummary, Money


class FeedbackGenerator:
    """AIを使用したフィードバック生成サービス."""

    def __init__(
        self,
        ai_client: AIClient,
        race_data_provider: RaceDataProvider,
    ) -> None:
        """初期化."""
        self._ai_client = ai_client
        self._race_data_provider = race_data_provider

    def generate_data_feedbacks(
        self, cart_items: list[CartItem]
    ) -> list[DataFeedback]:
        """各買い目に対するデータフィードバックを生成する."""
        feedbacks = []

        for item in cart_items:
            # レースと出走馬の情報を取得
            runners = self._race_data_provider.get_runners(item.race_id)
            selected_numbers = item.get_selected_numbers().to_list()

            horse_summaries = []
            horse_names = []
            recent_results = []
            jockey_stats = []
            track_suitability = []
            current_odds = []

            for runner in runners:
                if runner.horse_number in selected_numbers:
                    # 過去成績を取得
                    past_perf = self._race_data_provider.get_past_performance(
                        runner.horse_id
                    )
                    recent = self._format_recent_results(past_perf[:5]) if past_perf else "データなし"

                    # 騎手成績を取得
                    race_data = self._race_data_provider.get_race(item.race_id)
                    course = f"{race_data.venue}" if race_data else ""
                    jockey_data = self._race_data_provider.get_jockey_stats(
                        runner.jockey_id, course
                    )
                    jockey_stat = (
                        f"勝率{jockey_data.win_rate*100:.1f}%"
                        if jockey_data
                        else "データなし"
                    )

                    summary = HorseDataSummary(
                        horse_number=runner.horse_number,
                        horse_name=runner.horse_name,
                        recent_results=recent,
                        jockey_stats=jockey_stat,
                        track_suitability="",  # AIが生成
                        current_odds=runner.odds,
                        popularity=runner.popularity,
                    )
                    horse_summaries.append(summary)
                    horse_names.append(runner.horse_name)
                    recent_results.append(recent)
                    jockey_stats.append(jockey_stat)
                    track_suitability.append("")
                    current_odds.append(runner.odds)

            # AIでフィードバックコメントを生成
            context = BetFeedbackContext(
                race_name=item.race_name,
                horse_numbers=selected_numbers,
                horse_names=horse_names,
                recent_results=recent_results,
                jockey_stats=jockey_stats,
                track_suitability=track_suitability,
                current_odds=current_odds,
            )
            overall_comment = self._ai_client.generate_bet_feedback(context)

            feedback = DataFeedback.create(
                cart_item_id=item.item_id,
                horse_summaries=horse_summaries,
                overall_comment=overall_comment,
            )
            feedbacks.append(feedback)

        return feedbacks

    def generate_amount_feedback(
        self,
        total_amount: Money,
        remaining_loss_limit: Money | None = None,
        average_amount: Money | None = None,
    ) -> AmountFeedback:
        """掛け金フィードバックを生成する."""
        # AmountFeedback.createが警告レベルとコメントを自動生成
        return AmountFeedback.create(
            total_amount=total_amount,
            remaining_loss_limit=remaining_loss_limit,
            average_amount=average_amount,
        )

    def _format_recent_results(self, performances: list) -> str:
        """過去成績をフォーマットする."""
        if not performances:
            return "データなし"
        positions = [str(p.finish_position) for p in performances]
        return "-".join(positions)
