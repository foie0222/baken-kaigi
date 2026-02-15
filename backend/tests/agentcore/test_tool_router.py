"""ツールルーターのテスト."""

import sys
from pathlib import Path

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))


class Testツールルーター:
    """get_tools のテスト."""

    def test_get_toolsは2つのツールを返す(self):
        from tool_router import get_tools

        tools = get_tools()
        assert len(tools) == 2

    def test_get_toolsはanalyze_race_for_bettingを含む(self):
        from tool_router import get_tools

        tools = get_tools()
        names = [t.__name__ for t in tools]
        assert "analyze_race_for_betting" in names

    def test_get_toolsはpropose_betsを含む(self):
        from tool_router import get_tools

        tools = get_tools()
        names = [t.__name__ for t in tools]
        assert "propose_bets" in names
