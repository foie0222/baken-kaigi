"""負け額限度額チェック結果の値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import WarningLevel
from .money import Money


@dataclass(frozen=True)
class LossLimitCheckResult:
    """負け額限度額のチェック結果."""

    can_purchase: bool
    remaining_amount: Money | None
    warning_level: WarningLevel
    message: str
