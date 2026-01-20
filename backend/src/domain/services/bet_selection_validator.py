"""買い目検証サービス."""
from dataclasses import dataclass
from datetime import datetime

from ..value_objects import BetSelection, RaceReference


@dataclass(frozen=True)
class ValidationResult:
    """検証結果."""

    is_valid: bool
    errors: tuple[str, ...]

    @classmethod
    def success(cls) -> "ValidationResult":
        """成功結果を生成する."""
        return cls(is_valid=True, errors=())

    @classmethod
    def failure(cls, errors: list[str]) -> "ValidationResult":
        """失敗結果を生成する."""
        return cls(is_valid=False, errors=tuple(errors))


class BetSelectionValidator:
    """買い目の検証サービス."""

    def validate(self, bet_selection: BetSelection) -> ValidationResult:
        """買い目が有効かどうかを検証する."""
        errors: list[str] = []

        # 券種に対する馬番数のチェック
        required = bet_selection.bet_type.get_required_count()
        actual = bet_selection.horse_numbers.count()
        if actual != required:
            errors.append(
                f"{bet_selection.bet_type.get_display_name()}は{required}頭選択が必要です（現在{actual}頭）"
            )

        # 金額のチェック
        if not bet_selection.amount.is_valid_bet_amount():
            errors.append("金額は100円以上、100円単位で指定してください")

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def validate_for_race(
        self,
        bet_selection: BetSelection,
        race_ref: RaceReference,
        now: datetime,
    ) -> ValidationResult:
        """レース情報を考慮した検証を行う."""
        # 基本検証
        result = self.validate(bet_selection)
        errors = list(result.errors)

        # 締め切りチェック
        if not race_ref.is_before_deadline(now):
            errors.append(f"{race_ref.race_name}の投票締め切りを過ぎています")

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()
