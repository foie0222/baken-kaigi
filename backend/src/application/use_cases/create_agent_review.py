"""エージェント振り返り生成ユースケース."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.domain.entities import AgentReview, BetResult
from src.domain.identifiers import AgentId, RaceId, ReviewId, UserId
from src.domain.ports.agent_repository import AgentRepository
from src.domain.ports.agent_review_repository import AgentReviewRepository

from .get_agent import AgentNotFoundError


class ReviewAlreadyExistsError(Exception):
    """同一レースの振り返りが既に存在する場合のエラー."""


@dataclass(frozen=True)
class CreateAgentReviewResult:
    """振り返り生成結果."""

    review: AgentReview


class CreateAgentReviewUseCase:
    """エージェント振り返り生成ユースケース.

    レース結果を受け取り、振り返りテキストを生成する。
    Phase 1ではルールベースの簡易実装。
    """

    def __init__(
        self,
        agent_repository: AgentRepository,
        review_repository: AgentReviewRepository,
    ) -> None:
        """初期化."""
        self._agent_repository = agent_repository
        self._review_repository = review_repository

    def execute(
        self,
        user_id: str,
        race_id: str,
        race_date: str,
        race_name: str,
        bets: list[dict],
    ) -> CreateAgentReviewResult:
        """振り返りを生成する.

        Args:
            user_id: ユーザーID
            race_id: レースID
            race_date: レース日付 (YYYY-MM-DD)
            race_name: レース名
            bets: 賭け結果リスト [{bet_type, horse_numbers, amount, result, payout}]

        Returns:
            振り返り生成結果

        Raises:
            AgentNotFoundError: エージェントが見つからない場合
            ReviewAlreadyExistsError: 同一レースの振り返りが既に存在する場合
            ValueError: パラメータが不正な場合
        """
        uid = UserId(user_id)
        agent = self._agent_repository.find_by_user_id(uid)

        if agent is None:
            raise AgentNotFoundError(f"Agent not found for user: {user_id}")

        # 同一レースの振り返り重複チェック
        if self._review_repository.exists_by_agent_and_race(agent.agent_id, RaceId(race_id)):
            raise ReviewAlreadyExistsError(f"Review already exists for race: {race_id}")

        if not bets:
            raise ValueError("At least one bet result is required")

        # 賭け結果を変換
        bet_results = []
        total_invested = 0
        total_return = 0
        for b in bets:
            br = BetResult(
                bet_type=b["bet_type"],
                horse_numbers=b["horse_numbers"],
                amount=b["amount"],
                result=b["result"],
                payout=b["payout"],
            )
            bet_results.append(br)
            total_invested += br.amount
            total_return += br.payout

        has_win = any(br.result == "hit" for br in bet_results)
        profit = total_return - total_invested

        # 振り返りテキストを生成（Phase 1: ルールベース）
        review_text = self._generate_review_text(
            race_name, bet_results, total_invested, total_return, has_win, profit,
        )

        # 学びを生成
        learnings = self._generate_learnings(bet_results, has_win, profit)

        # 振り返りエンティティ作成
        review_id = ReviewId(f"rev_{uuid.uuid4().hex[:12]}")
        review = AgentReview(
            review_id=review_id,
            agent_id=agent.agent_id,
            race_id=RaceId(race_id),
            race_date=race_date,
            race_name=race_name,
            bet_results=bet_results,
            total_invested=total_invested,
            total_return=total_return,
            review_text=review_text,
            learnings=learnings,
            stats_change={},
        )

        self._review_repository.save(review)

        return CreateAgentReviewResult(review=review)

    def _generate_review_text(
        self,
        race_name: str,
        bet_results: list[BetResult],
        total_invested: int,
        total_return: int,
        has_win: bool,
        profit: int,
    ) -> str:
        """振り返りテキストを生成する."""
        if has_win and profit > 0:
            return (
                f"{race_name}では的中がありました。"
                f"投資{total_invested:,}円に対して{total_return:,}円の回収、"
                f"収支は+{profit:,}円でした。"
                f"良い判断ができたレースです。"
            )
        elif has_win and profit <= 0:
            return (
                f"{race_name}では的中はありましたが、"
                f"投資{total_invested:,}円に対して{total_return:,}円の回収で"
                f"収支は{profit:,}円でした。"
                f"買い目をもっと絞り込む必要があります。"
            )
        else:
            return (
                f"{race_name}は残念ながら不的中でした。"
                f"投資{total_invested:,}円のマイナスです。"
                f"次のレースに向けて分析を磨きましょう。"
            )

    def _generate_learnings(
        self,
        bet_results: list[BetResult],
        has_win: bool,
        profit: int,
    ) -> list[str]:
        """学びを生成する."""
        learnings = []

        if has_win and profit > 0:
            learnings.append("的中して利益が出た。良い買い目選びだった")
        elif has_win and profit <= 0:
            learnings.append("的中はしたがトリガミ。買い目を絞る必要がある")
        else:
            learnings.append("不的中。次回は分析をより慎重に")

        total = len(bet_results)
        hit_count = sum(1 for b in bet_results if b.result == "hit")
        if total > 1 and hit_count == 0:
            learnings.append(f"{total}点すべて不的中。点数が多すぎる可能性")
        elif total > 1 and hit_count > 0:
            learnings.append(f"{total}点中{hit_count}点的中")

        return learnings

