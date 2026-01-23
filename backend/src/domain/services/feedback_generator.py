"""フィードバック生成サービス."""
from datetime import datetime

from ..entities import CartItem
from ..ports import AIClient, BetFeedbackContext, PedigreeData, RaceDataProvider, WeightData
from ..value_objects import AmountFeedback, DataFeedback, HorseDataSummary, Money

# 馬体重傾向判定の定数
WEIGHT_HISTORY_LIMIT = 5  # 傾向判定に使用する直近レース数
WEIGHT_TREND_THRESHOLD = 2  # この値(kg)を超えると増加/減少傾向と判定


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
            # レース情報を取得（ループ外で1回だけ）
            race_data = self._race_data_provider.get_race(item.race_id)
            course = f"{race_data.venue}" if race_data else ""

            # 出走馬情報を取得
            runners = self._race_data_provider.get_runners(item.race_id)
            selected_numbers = item.get_selected_numbers().to_list()

            # レースの馬体重情報を取得（馬番 -> WeightData）
            race_weights = self._race_data_provider.get_race_weights(item.race_id)

            # 選択馬のhorse_idを収集してバッチ取得の準備
            selected_runners = [r for r in runners if r.horse_number in selected_numbers]
            horse_ids = [r.horse_id for r in selected_runners]

            # 血統情報をバッチ取得（現状APIが個別取得のみ対応のため、一括で取得してキャッシュ）
            pedigree_cache: dict[str, PedigreeData | None] = {}
            weight_history_cache: dict[str, list[WeightData]] = {}
            for horse_id in horse_ids:
                pedigree_cache[horse_id] = self._race_data_provider.get_pedigree(horse_id)
                weight_history_cache[horse_id] = self._race_data_provider.get_weight_history(
                    horse_id, limit=WEIGHT_HISTORY_LIMIT
                )

            horse_summaries = []
            horse_names = []
            recent_results = []
            jockey_stats = []
            track_suitability = []
            current_odds = []

            for runner in selected_runners:
                # 過去成績を取得
                past_perf = self._race_data_provider.get_past_performance(
                    runner.horse_id
                )
                recent = self._format_recent_results(past_perf[:5]) if past_perf else "データなし"

                # 騎手成績を取得
                jockey_data = self._race_data_provider.get_jockey_stats(
                    runner.jockey_id, course
                )
                jockey_stat = (
                    f"勝率{jockey_data.win_rate*100:.1f}%"
                    if jockey_data
                    else "データなし"
                )

                # 血統情報を取得（キャッシュから）
                pedigree_data = pedigree_cache.get(runner.horse_id)
                pedigree = self._format_pedigree(pedigree_data)

                # 馬体重を取得
                weight_data = race_weights.get(runner.horse_number)
                weight_current = weight_data.weight if weight_data else None

                # 馬体重の傾向を取得（キャッシュから）
                weight_history = weight_history_cache.get(runner.horse_id, [])
                weight_trend = self._calculate_weight_trend(weight_history)

                summary = HorseDataSummary(
                    horse_number=runner.horse_number,
                    horse_name=runner.horse_name,
                    recent_results=recent,
                    jockey_stats=jockey_stat,
                    track_suitability="",  # AIが生成
                    current_odds=runner.odds,
                    popularity=runner.popularity,
                    pedigree=pedigree,
                    weight_trend=weight_trend,
                    weight_current=weight_current,
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

    def _format_pedigree(self, pedigree_data: PedigreeData | None) -> str | None:
        """血統情報を "父:〇〇 母父:△△" 形式にフォーマットする."""
        if not pedigree_data:
            return None

        sire = pedigree_data.sire_name.strip() if pedigree_data.sire_name else None
        broodmare_sire = pedigree_data.broodmare_sire.strip() if pedigree_data.broodmare_sire else None

        if not sire and not broodmare_sire:
            return None

        parts = []
        if sire:
            parts.append(f"父:{sire}")
        if broodmare_sire:
            parts.append(f"母父:{broodmare_sire}")

        return " ".join(parts) if parts else None

    def _calculate_weight_trend(self, weight_history: list[WeightData]) -> str | None:
        """馬体重履歴から傾向を判定する.

        Returns:
            "増加傾向" / "安定" / "減少傾向" / None
        """
        if not weight_history or len(weight_history) < 2:
            return None

        # 直近の増減を集計
        total_diff = sum(w.weight_diff for w in weight_history)
        avg_diff = total_diff / len(weight_history)

        if avg_diff > WEIGHT_TREND_THRESHOLD:
            return "増加傾向"
        elif avg_diff < -WEIGHT_TREND_THRESHOLD:
            return "減少傾向"
        else:
            return "安定"
