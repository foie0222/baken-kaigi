"""IPAT残高を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpatBalance:
    """IPAT口座の残高情報."""

    bet_dedicated_balance: int
    settle_possible_balance: int
    bet_balance: int
    limit_vote_amount: int
