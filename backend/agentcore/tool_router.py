"""ツールルーター - エージェントが使用するツールセットを提供."""

from typing import Any, Callable


def get_tools() -> list[Callable[..., Any]]:
    """エージェントが使用するツールリストを返す."""
    from tools.race_analyzer import analyze_race_for_betting
    from tools.ev_proposer import propose_bets

    return [analyze_race_for_betting, propose_bets]
