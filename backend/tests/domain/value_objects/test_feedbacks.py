"""フィードバック値オブジェクト（HorseDataSummary, DataFeedback, AmountFeedback）のテスト."""
from datetime import datetime

import pytest

from src.domain.value_objects import AmountFeedback
from src.domain.value_objects import DataFeedback
from src.domain.value_objects import HorseDataSummary
from src.domain.identifiers import ItemId
from src.domain.value_objects import Money
from src.domain.enums import WarningLevel


class TestHorseDataSummary:
    """HorseDataSummaryの単体テスト."""

    def test_有効なデータで生成できる(self) -> None:
        """有効なデータでHorseDataSummaryを生成できることを確認."""
        summary = HorseDataSummary(
            horse_number=5,
            horse_name="ディープインパクト",
            recent_results="1-1-2-1-3",
            jockey_stats="勝率20%",
            track_suitability="良馬場得意",
            current_odds="2.5",
            popularity=1,
        )
        assert summary.horse_number == 5
        assert summary.horse_name == "ディープインパクト"

    def test_馬番が0でエラー(self) -> None:
        """馬番が0だとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="between 1 and 18"):
            HorseDataSummary(
                horse_number=0,
                horse_name="テスト",
                recent_results="",
                jockey_stats="",
                track_suitability="",
                current_odds="",
                popularity=1,
            )

    def test_馬番が19でエラー(self) -> None:
        """馬番が19だとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="between 1 and 18"):
            HorseDataSummary(
                horse_number=19,
                horse_name="テスト",
                recent_results="",
                jockey_stats="",
                track_suitability="",
                current_odds="",
                popularity=1,
            )

    def test_空の馬名でエラー(self) -> None:
        """空の馬名を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            HorseDataSummary(
                horse_number=1,
                horse_name="",
                recent_results="",
                jockey_stats="",
                track_suitability="",
                current_odds="",
                popularity=1,
            )

    def test_人気順が0以下でエラー(self) -> None:
        """人気順が0以下だとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="at least 1"):
            HorseDataSummary(
                horse_number=1,
                horse_name="テスト",
                recent_results="",
                jockey_stats="",
                track_suitability="",
                current_odds="",
                popularity=0,
            )


class TestDataFeedback:
    """DataFeedbackの単体テスト."""

    def test_有効なデータで生成できる(self) -> None:
        """有効なデータでDataFeedbackを生成できることを確認."""
        summary = HorseDataSummary(
            horse_number=1,
            horse_name="テスト馬",
            recent_results="1-1-1",
            jockey_stats="勝率30%",
            track_suitability="良馬場得意",
            current_odds="3.0",
            popularity=2,
        )
        feedback = DataFeedback(
            cart_item_id=ItemId("item-1"),
            horse_summaries=(summary,),
            overall_comment="総合的に良い買い目です",
            generated_at=datetime(2024, 1, 1, 12, 0),
        )
        assert feedback.overall_comment == "総合的に良い買い目です"

    def test_createで生成できる(self) -> None:
        """createメソッドでDataFeedbackを生成できることを確認."""
        summary = HorseDataSummary(
            horse_number=1,
            horse_name="テスト馬",
            recent_results="",
            jockey_stats="",
            track_suitability="",
            current_odds="",
            popularity=1,
        )
        feedback = DataFeedback.create(
            cart_item_id=ItemId("item-1"),
            horse_summaries=[summary],
            overall_comment="コメント",
        )
        assert feedback.cart_item_id.value == "item-1"

    def test_空のhorse_summariesでエラー(self) -> None:
        """空のhorse_summariesを指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DataFeedback(
                cart_item_id=ItemId("item-1"),
                horse_summaries=(),
                overall_comment="コメント",
                generated_at=datetime.now(),
            )

    def test_空のoverall_commentでエラー(self) -> None:
        """空のoverall_commentを指定するとValueErrorが発生することを確認."""
        summary = HorseDataSummary(
            horse_number=1,
            horse_name="テスト馬",
            recent_results="",
            jockey_stats="",
            track_suitability="",
            current_odds="",
            popularity=1,
        )
        with pytest.raises(ValueError, match="cannot be empty"):
            DataFeedback(
                cart_item_id=ItemId("item-1"),
                horse_summaries=(summary,),
                overall_comment="",
                generated_at=datetime.now(),
            )

    def test_get_horse_summaryで馬番から要約を取得(self) -> None:
        """get_horse_summaryで指定馬番の要約を取得できることを確認."""
        summary1 = HorseDataSummary(
            horse_number=1,
            horse_name="馬1",
            recent_results="",
            jockey_stats="",
            track_suitability="",
            current_odds="",
            popularity=1,
        )
        summary5 = HorseDataSummary(
            horse_number=5,
            horse_name="馬5",
            recent_results="",
            jockey_stats="",
            track_suitability="",
            current_odds="",
            popularity=2,
        )
        feedback = DataFeedback.create(
            cart_item_id=ItemId("item-1"),
            horse_summaries=[summary1, summary5],
            overall_comment="コメント",
        )
        assert feedback.get_horse_summary(5).horse_name == "馬5"
        assert feedback.get_horse_summary(10) is None


class TestAmountFeedback:
    """AmountFeedbackの単体テスト."""

    def test_createで警告レベルが自動判定される_NONE(self) -> None:
        """createで限度額の80%未満の場合NONEになることを確認."""
        feedback = AmountFeedback.create(
            total_amount=Money(7000),
            remaining_loss_limit=Money(10000),
        )
        assert feedback.warning_level == WarningLevel.NONE
        assert feedback.is_limit_exceeded is False

    def test_createで警告レベルが自動判定される_CAUTION(self) -> None:
        """createで限度額の80%以上100%未満の場合CAUTIONになることを確認."""
        feedback = AmountFeedback.create(
            total_amount=Money(8500),
            remaining_loss_limit=Money(10000),
        )
        assert feedback.warning_level == WarningLevel.CAUTION
        assert feedback.is_limit_exceeded is False

    def test_createで警告レベルが自動判定される_WARNING(self) -> None:
        """createで限度額超過の場合WARNINGになることを確認."""
        feedback = AmountFeedback.create(
            total_amount=Money(12000),
            remaining_loss_limit=Money(10000),
        )
        assert feedback.warning_level == WarningLevel.WARNING
        assert feedback.is_limit_exceeded is True

    def test_createで限度額なしの場合NONEになる(self) -> None:
        """createで限度額が未設定の場合NONEになることを確認."""
        feedback = AmountFeedback.create(
            total_amount=Money(50000),
            remaining_loss_limit=None,
        )
        assert feedback.warning_level == WarningLevel.NONE
        assert feedback.is_limit_exceeded is False

    def test_コメントが自動生成される(self) -> None:
        """createでコメントが自動生成されることを確認."""
        feedback = AmountFeedback.create(
            total_amount=Money(5000),
            remaining_loss_limit=Money(10000),
        )
        assert "¥5,000" in feedback.comment
        assert "¥10,000" in feedback.comment

    def test_空のコメントでエラー(self) -> None:
        """空のコメントを指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AmountFeedback(
                total_amount=Money(1000),
                remaining_loss_limit=None,
                average_amount=None,
                is_limit_exceeded=False,
                warning_level=WarningLevel.NONE,
                comment="",
                generated_at=datetime.now(),
            )
