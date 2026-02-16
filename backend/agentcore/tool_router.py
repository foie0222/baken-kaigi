"""ツールルーター - エージェントが使用するツールセットを提供."""

from collections.abc import Callable
from typing import Any


def get_tools() -> list[Callable[..., Any]]:
    """エージェントが使用するツールリストを返す."""
    from tools.ev_proposer import propose_bets
    from tools.race_analyzer import analyze_race_for_betting

    return [analyze_race_for_betting, propose_bets]
