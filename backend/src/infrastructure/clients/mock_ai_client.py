"""モックAIクライアント."""
import random

from src.domain.entities import Message
from src.domain.ports import (
    AIClient,
    AmountFeedbackContext,
    BetFeedbackContext,
    ConsultationContext,
)


class MockAIClient(AIClient):
    """モックAIクライアント（開発・デモ用）."""

    # フィードバックテンプレート
    BET_FEEDBACK_TEMPLATES = [
        "【データ分析】選択された馬について、過去の成績とコース適性を確認しました。"
        "複数の観点から検討することで、より良い判断ができるでしょう。",
        "【傾向分析】この組み合わせは統計的に興味深い特徴があります。"
        "ただし、過去のデータは将来を保証するものではありません。",
        "【客観的視点】選択された買い目について、いくつかのデータポイントを確認しました。"
        "最終判断はご自身の判断で行ってください。",
    ]

    AMOUNT_FEEDBACK_HEALTHY = [
        "掛け金は適切な範囲に見えます。楽しむ範囲で続けましょう。",
        "現在の掛け金は無理のない範囲です。この調子で計画的に。",
        "バランスの取れた金額設定です。引き続き冷静な判断を。",
    ]

    AMOUNT_FEEDBACK_WARNING = [
        "掛け金が上限に近づいています。一度立ち止まって考えましょう。",
        "設定した上限を意識してください。熱くなりすぎていませんか？",
        "今日の予算を確認しましょう。計画的な賭け方が大切です。",
    ]

    AMOUNT_FEEDBACK_EXCEEDED = [
        "設定した上限を超えています。今日はここまでにしませんか？",
        "損失上限を超過しています。一度クールダウンすることをお勧めします。",
        "上限超過です。明日また新たな気持ちで挑戦しましょう。",
    ]

    CONVERSATION_RESPONSES = [
        "なるほど、{topic}についてですね。"
        "データを見ると興味深い傾向がありますが、最終判断はあなた次第です。",
        "{topic}に関するご質問ですね。"
        "過去のデータは参考になりますが、今回も同じ結果になるとは限りません。",
        "{topic}について考えているのですね。"
        "色々な角度から検討することが大切です。焦らずじっくり考えましょう。",
    ]

    def generate_bet_feedback(self, context: BetFeedbackContext) -> str:
        """買い目データに基づくフィードバック文を生成する."""
        base_feedback = random.choice(self.BET_FEEDBACK_TEMPLATES)

        # 馬ごとの詳細フィードバックを生成
        details = []
        for i, (number, name) in enumerate(
            zip(context.horse_numbers, context.horse_names, strict=False)
        ):
            recent = context.recent_results[i] if i < len(context.recent_results) else "データなし"
            jockey = context.jockey_stats[i] if i < len(context.jockey_stats) else "データなし"
            suitability = (
                context.track_suitability[i]
                if i < len(context.track_suitability)
                else "不明"
            )
            odds = context.current_odds[i] if i < len(context.current_odds) else "---"

            details.append(
                f"\n【{number}番 {name}】\n"
                f"  近走: {recent}\n"
                f"  騎手: {jockey}\n"
                f"  適性: {suitability}\n"
                f"  オッズ: {odds}倍"
            )

        return base_feedback + "\n" + "\n".join(details)

    def generate_amount_feedback(self, context: AmountFeedbackContext) -> str:
        """掛け金に関するフィードバック文を生成する."""
        if context.is_limit_exceeded:
            feedback = random.choice(self.AMOUNT_FEEDBACK_EXCEEDED)
        elif context.remaining_loss_limit is not None:
            if context.remaining_loss_limit < context.total_amount * 2:
                feedback = random.choice(self.AMOUNT_FEEDBACK_WARNING)
            else:
                feedback = random.choice(self.AMOUNT_FEEDBACK_HEALTHY)
        else:
            feedback = random.choice(self.AMOUNT_FEEDBACK_HEALTHY)

        # 詳細情報を追加
        details = f"\n\n【現在の状況】\n合計掛け金: ¥{context.total_amount:,}"
        if context.remaining_loss_limit is not None:
            details += f"\n残り損失上限: ¥{context.remaining_loss_limit:,}"
        if context.average_amount is not None:
            details += f"\n平均掛け金: ¥{context.average_amount:,}"

        return feedback + details

    def generate_conversation_response(
        self, messages: list[Message], context: ConsultationContext
    ) -> str:
        """自由会話の応答を生成する."""
        # 最後のユーザーメッセージからトピックを抽出
        topic = "買い目"
        if messages:
            last_message = messages[-1]
            if "オッズ" in last_message.content:
                topic = "オッズ"
            elif "騎手" in last_message.content:
                topic = "騎手"
            elif "成績" in last_message.content:
                topic = "過去の成績"
            elif "直感" in last_message.content:
                topic = "直感"
            elif "金額" in last_message.content or "掛け" in last_message.content:
                topic = "掛け金"

        response = random.choice(self.CONVERSATION_RESPONSES).format(topic=topic)

        # コンテキスト情報を追加
        response += f"\n\n【参考情報】\n{context.data_feedback_summary}"

        return response
