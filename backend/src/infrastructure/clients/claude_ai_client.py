# -*- coding: utf-8 -*-
"""Claude AI クライアント実装."""
import os

import anthropic

from src.domain.entities import Message
from src.domain.enums import MessageType
from src.domain.ports import (
    AIClient,
    AmountFeedbackContext,
    BetFeedbackContext,
    ConsultationContext,
)


class ClaudeAIClient(AIClient):
    """Claude API を使用した AI クライアント."""

    def __init__(self) -> None:
        """初期化."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    def generate_bet_feedback(self, context: BetFeedbackContext) -> str:
        """買い目データに基づくフィードバック文を生成する."""
        horse_details = []
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

            horse_details.append(
                f"- {number}番 {name}: 近走={recent}, 騎手={jockey}, 適性={suitability}, オッズ={odds}倍"
            )

        prompt = f"""あなたは競馬の買い目分析をサポートするAIアシスタントです。
ユーザーが選択した買い目について、客観的なデータに基づいたフィードバックを提供してください。

【重要】
- あなたは「推奨」や「おすすめ」をしてはいけません
- ギャンブルを促進する表現は避けてください
- 「最終判断はご自身で行ってください」という姿勢を保ってください
- データに基づく客観的な分析のみを提供してください

レース: {context.race_name}

選択された馬:
{chr(10).join(horse_details)}

上記のデータを基に、200文字以内で客観的なフィードバックを提供してください。"""

        response = self._client.messages.create(
            model=self._model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def generate_amount_feedback(self, context: AmountFeedbackContext) -> str:
        """掛け金に関するフィードバック文を生成する."""
        status = "健全"
        if context.is_limit_exceeded:
            status = "上限超過"
        elif context.remaining_loss_limit is not None:
            if context.remaining_loss_limit < context.total_amount * 2:
                status = "上限接近中"

        prompt = f"""あなたは責任あるギャンブルを促進するAIアシスタントです。
ユーザーの掛け金について、適切なフィードバックを提供してください。

【重要】
- ギャンブル依存症の予防を意識した発言をしてください
- 無理な賭けを促すような表現は絶対に避けてください
- 「立ち止まって考えましょう」という姿勢を保ってください

掛け金状況:
- 合計掛け金: ¥{context.total_amount:,}
- 残り損失上限: {f'¥{context.remaining_loss_limit:,}' if context.remaining_loss_limit else '未設定'}
- 過去平均掛け金: {f'¥{context.average_amount:,}' if context.average_amount else '不明'}
- 状態: {status}

上記の状況を基に、100文字以内で適切なフィードバックを提供してください。
上限超過の場合は、今日はここで終わりにすることを強く勧めてください。"""

        response = self._client.messages.create(
            model=self._model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def generate_conversation_response(
        self, messages: list[Message], context: ConsultationContext
    ) -> str:
        """自由会話の応答を生成する."""
        # 会話履歴を構築
        conversation = []
        for msg in messages:
            role = "user" if msg.type == MessageType.USER else "assistant"
            conversation.append({"role": role, "content": msg.content})

        system_prompt = f"""あなたは競馬の買い目について相談に乗るAIアシスタント「馬券会議AI」です。

【重要なルール】
- あなたは「推奨」や「この馬を買うべき」といった助言をしてはいけません
- ギャンブルを促進する表現は避けてください
- 「最終判断はご自身で行ってください」という姿勢を保ってください
- データに基づく客観的な情報提供のみを行ってください
- ユーザーが熱くなりすぎている場合は、冷静になるよう促してください

【現在の相談内容】
カート概要: {context.cart_summary}
データフィードバック: {context.data_feedback_summary}
掛け金フィードバック: {context.amount_feedback_summary}

ユーザーの質問に対して、上記の情報を参考に150文字以内で回答してください。"""

        response = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=system_prompt,
            messages=conversation if conversation else [{"role": "user", "content": "こんにちは"}],
        )

        return response.content[0].text
