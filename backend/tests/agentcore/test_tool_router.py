"""ツールルーターのテスト."""

import sys
from pathlib import Path

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tool_router import classify_question, get_tools_for_category, TOOL_CATEGORIES


# =============================================================================
# classify_question のテスト
# =============================================================================


class TestClassifyQuestion:
    """classify_question のテスト."""

    # --- full_analysis ---

    def test_カート分析依頼はfull_analysis(self):
        result = classify_question("カートの買い目を分析してください", has_cart=True)
        assert result == "full_analysis"

    def test_カートありで診断キーワードはfull_analysis(self):
        result = classify_question("この買い目は大丈夫ですか？", has_cart=True)
        assert result == "full_analysis"

    def test_カートありでチェックキーワードはfull_analysis(self):
        result = classify_question("カートの中身をチェックして", has_cart=True)
        assert result == "full_analysis"

    # --- horse_focused ---

    def test_馬に関する質問はhorse_focused(self):
        result = classify_question("3番の馬の過去成績は？")
        assert result == "horse_focused"

    def test_騎手に関する質問はhorse_focused(self):
        result = classify_question("この騎手の最近の成績は？")
        assert result == "horse_focused"

    def test_調教に関する質問はhorse_focused(self):
        result = classify_question("調教の動きはどうですか？")
        assert result == "horse_focused"

    def test_血統に関する質問はhorse_focused(self):
        result = classify_question("この馬の血統的にダートは合う？")
        assert result == "horse_focused"

    def test_体重に関する質問はhorse_focused(self):
        result = classify_question("馬体重の増減はどう？")
        assert result == "horse_focused"

    # --- bet_focused ---

    def test_買い目に関する質問はbet_focused(self):
        result = classify_question("この買い目のオッズはどう？")
        assert result == "bet_focused"

    def test_期待値に関する質問はbet_focused(self):
        result = classify_question("期待値が高い馬券は？")
        assert result == "bet_focused"

    def test_トリガミに関する質問はbet_focused(self):
        result = classify_question("トリガミになりそうな馬券は？")
        assert result == "bet_focused"

    def test_券種に関する質問はbet_focused(self):
        result = classify_question("おすすめの券種は？")
        assert result == "bet_focused"

    # --- race_focused ---

    def test_展開に関する質問はrace_focused(self):
        result = classify_question("このレースの展開予想は？")
        assert result == "race_focused"

    def test_ペースに関する質問はrace_focused(self):
        result = classify_question("ペースはどうなりそう？")
        assert result == "race_focused"

    def test_馬場に関する質問はrace_focused(self):
        result = classify_question("馬場状態とコースの影響は？")
        assert result == "race_focused"

    def test_逃げ先行に関する質問はrace_focused(self):
        result = classify_question("逃げ馬はいる？先行有利？")
        assert result == "race_focused"

    # --- risk_focused ---

    def test_リスクに関する質問はrisk_focused(self):
        result = classify_question("リスクや危険な点はある？")
        assert result == "risk_focused"

    def test_見送りに関する質問はrisk_focused(self):
        result = classify_question("このレースは見送りにすべき？")
        assert result == "risk_focused"

    def test_注意点に関する質問はrisk_focused(self):
        result = classify_question("注意すべきポイントは？")
        assert result == "risk_focused"

    def test_不安に関する質問はrisk_focused(self):
        result = classify_question("不安な要素はありますか？")
        assert result == "risk_focused"

    # --- followup ---

    def test_一般的な追加質問はfollowup(self):
        result = classify_question("ありがとう、他に何かある？")
        assert result == "followup"

    def test_感想のみの返答はfollowup(self):
        result = classify_question("なるほど、わかりました")
        assert result == "followup"

    def test_空メッセージはfollowup(self):
        result = classify_question("")
        assert result == "followup"

    # --- 複数カテゴリのキーワードを含む場合 ---

    def test_複数カテゴリは最多ヒットのカテゴリ(self):
        # "馬" と "オッズ" の両方を含む場合
        result = classify_question("この馬のオッズの動きはどう？")
        assert result in ("horse_focused", "bet_focused")

    def test_カートなしでキーワードヒットはカテゴリ分類(self):
        # カートがなくても馬キーワードならhorse_focused
        result = classify_question("この馬はどう思う？", has_cart=False)
        assert result == "horse_focused"

    # --- has_cart / has_runners の影響 ---

    def test_カートありでもキーワード不一致はカテゴリ分類(self):
        # カートがあってもfull_analysisキーワードがなければ別カテゴリ
        result = classify_question("この馬の血統は？", has_cart=True)
        assert result == "horse_focused"

    def test_出走馬データありでキーワードなしはfull_analysis(self):
        result = classify_question("どう思う？", has_runners=True)
        assert result == "full_analysis"

    def test_カートも出走馬もなくキーワードなしはfollowup(self):
        result = classify_question("よろしくお願いします", has_cart=False, has_runners=False)
        assert result == "followup"


# =============================================================================
# get_tools_for_category のテスト
# =============================================================================


class TestGetToolsForCategory:
    """get_tools_for_category のテスト."""

    def test_full_analysisは全10ツール(self):
        tools = get_tools_for_category("full_analysis")
        assert len(tools) == 10

    def test_followupはツールなし(self):
        tools = get_tools_for_category("followup")
        assert len(tools) == 0

    def test_horse_focusedは5ツール(self):
        tools = get_tools_for_category("horse_focused")
        assert len(tools) == 5

    def test_bet_focusedは5ツール(self):
        tools = get_tools_for_category("bet_focused")
        assert len(tools) == 5

    def test_race_focusedは5ツール(self):
        tools = get_tools_for_category("race_focused")
        assert len(tools) == 5

    def test_risk_focusedは4ツール(self):
        tools = get_tools_for_category("risk_focused")
        assert len(tools) == 4

    def test_未知のカテゴリは全ツール(self):
        tools = get_tools_for_category("unknown_category")
        assert len(tools) == 10

    def test_full_analysisのツールはユニーク(self):
        tools = get_tools_for_category("full_analysis")
        assert len(tools) == len(set(id(t) for t in tools))

    def test_各カテゴリのツールはfull_analysisのサブセット(self):
        all_tools = set(id(t) for t in get_tools_for_category("full_analysis"))
        for category in TOOL_CATEGORIES:
            tools = get_tools_for_category(category)
            tool_ids = set(id(t) for t in tools)
            assert tool_ids.issubset(all_tools), f"{category} has tools not in full_analysis"


# =============================================================================
# TOOL_CATEGORIES の構造テスト
# =============================================================================


class TestToolCategories:
    """TOOL_CATEGORIES の構造テスト."""

    def test_全カテゴリにdescriptionがある(self):
        for category, config in TOOL_CATEGORIES.items():
            assert "description" in config, f"{category} has no description"
            assert isinstance(config["description"], str)

    def test_全カテゴリにkeywordsがある(self):
        for category, config in TOOL_CATEGORIES.items():
            assert "keywords" in config, f"{category} has no keywords"
            assert isinstance(config["keywords"], list)

    def test_必須カテゴリが存在する(self):
        expected = {"full_analysis", "horse_focused", "bet_focused", "race_focused", "risk_focused", "followup"}
        assert set(TOOL_CATEGORIES.keys()) == expected
