"""agentcore/prompts/agent_prompt.py のテスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentcore.prompts.agent_prompt import (
    LEVEL_TITLES,
    STYLE_DESCRIPTIONS,
    get_agent_prompt_addition,
    _build_performance_section,
    _build_stat_emphasis,
)
from agentcore.prompts.consultation import get_agent_system_prompt


def _make_agent_data(**overrides) -> dict:
    """テスト用のagent_dataを生成するヘルパー."""
    data = {
        "name": "ハヤテ",
        "base_style": "solid",
        "stats": {
            "data_analysis": 40,
            "pace_reading": 30,
            "risk_management": 50,
            "intuition": 20,
        },
        "performance": {
            "total_bets": 15,
            "wins": 5,
            "total_invested": 15000,
            "total_return": 18000,
        },
        "level": 2,
    }
    data.update(overrides)
    return data


class TestGetAgentPromptAddition:
    """get_agent_prompt_addition のテスト."""

    def test_エージェント名がプロンプトに含まれる(self):
        result = get_agent_prompt_addition(_make_agent_data(name="シンプウ"))
        assert "シンプウ" in result

    def test_レベルとレベル称号が含まれる(self):
        result = get_agent_prompt_addition(_make_agent_data(level=3))
        assert "Lv.3" in result
        assert "一人前" in result

    def test_堅実型のスタイル情報が含まれる(self):
        result = get_agent_prompt_addition(_make_agent_data(base_style="solid"))
        assert "堅実型" in result
        assert "リスク管理を重視" in result

    def test_穴狙い型のスタイル情報が含まれる(self):
        result = get_agent_prompt_addition(_make_agent_data(base_style="longshot"))
        assert "穴狙い型" in result
        assert "大穴を見抜く" in result

    def test_データ分析型のスタイル情報が含まれる(self):
        result = get_agent_prompt_addition(_make_agent_data(base_style="data"))
        assert "データ分析型" in result
        assert "冷静で論理的" in result

    def test_展開読み型のスタイル情報が含まれる(self):
        result = get_agent_prompt_addition(_make_agent_data(base_style="pace"))
        assert "展開読み型" in result
        assert "レースの流れを読む" in result

    def test_ステータス値がプロンプトに含まれる(self):
        result = get_agent_prompt_addition(_make_agent_data())
        assert "40/100" in result  # data_analysis
        assert "30/100" in result  # pace_reading
        assert "50/100" in result  # risk_management
        assert "20/100" in result  # intuition

    def test_最も高いステータスが得意分野として表示される(self):
        data = _make_agent_data(stats={
            "data_analysis": 20,
            "pace_reading": 60,
            "risk_management": 30,
            "intuition": 10,
        })
        result = get_agent_prompt_addition(data)
        assert "最も得意な領域: 展開読み" in result

    def test_パフォーマンス情報が含まれる(self):
        result = get_agent_prompt_addition(_make_agent_data())
        assert "15回" in result
        assert "+3,000円" in result

    def test_未経験エージェントのパフォーマンス表示(self):
        data = _make_agent_data(performance={
            "total_bets": 0, "wins": 0, "total_invested": 0, "total_return": 0,
        })
        result = get_agent_prompt_addition(data)
        assert "まだレース経験がありません" in result

    def test_不正なスタイルはdataにフォールバック(self):
        result = get_agent_prompt_addition(_make_agent_data(base_style="invalid"))
        assert "データ分析型" in result

    def test_デフォルト値でもエラーにならない(self):
        result = get_agent_prompt_addition({})
        assert "エージェント" in result
        assert "Lv.1" in result


class TestBuildPerformanceSection:
    """_build_performance_section のテスト."""

    def test_実績ありの場合(self):
        result = _build_performance_section(10, 3, 10000, 12000)
        assert "10回" in result
        assert "30.0%" in result
        assert "120.0%" in result
        assert "+2,000円" in result

    def test_実績なしの場合(self):
        result = _build_performance_section(0, 0, 0, 0)
        assert "まだレース経験がありません" in result

    def test_マイナス収支の表示(self):
        result = _build_performance_section(10, 2, 10000, 7000)
        assert "-3,000円" in result


class TestBuildStatEmphasis:
    """_build_stat_emphasis のテスト."""

    def test_データ分析力が高い場合の指示(self):
        result = _build_stat_emphasis(60, 20, 30, 10)
        assert "AI指数や統計数値" in result

    def test_展開読み力が高い場合の指示(self):
        result = _build_stat_emphasis(20, 60, 30, 10)
        assert "ペース予想と脚質相性" in result

    def test_リスク管理力が高い場合の指示(self):
        result = _build_stat_emphasis(20, 20, 60, 10)
        assert "トリガミリスクや資金管理" in result

    def test_直感力が高い場合の指示(self):
        result = _build_stat_emphasis(20, 20, 30, 60)
        assert "オッズの歪みや市場の見落とし" in result

    def test_全ステータス低い場合は成長途中メッセージ(self):
        result = _build_stat_emphasis(20, 20, 30, 10)
        assert "成長途中" in result

    def test_複数のステータスが高い場合は複数の指示(self):
        result = _build_stat_emphasis(60, 60, 30, 10)
        assert "AI指数や統計数値" in result
        assert "ペース予想と脚質相性" in result


class TestStyleDescriptions:
    """STYLE_DESCRIPTIONS の網羅性テスト."""

    def test_4つのスタイルが定義されている(self):
        assert len(STYLE_DESCRIPTIONS) == 4
        assert "solid" in STYLE_DESCRIPTIONS
        assert "longshot" in STYLE_DESCRIPTIONS
        assert "data" in STYLE_DESCRIPTIONS
        assert "pace" in STYLE_DESCRIPTIONS

    def test_各スタイルに必要なキーがある(self):
        for style, desc in STYLE_DESCRIPTIONS.items():
            assert "label" in desc, f"{style} missing label"
            assert "personality" in desc, f"{style} missing personality"
            assert "strengths" in desc, f"{style} missing strengths"
            assert "approach" in desc, f"{style} missing approach"


class TestLevelTitles:
    """LEVEL_TITLES の網羅性テスト."""

    def test_レベル1から10まで定義されている(self):
        for i in range(1, 11):
            assert i in LEVEL_TITLES, f"Level {i} missing"

    def test_レベル1は駆け出し(self):
        assert LEVEL_TITLES[1] == "駆け出し"

    def test_レベル10は神(self):
        assert LEVEL_TITLES[10] == "神"


class TestGetAgentSystemPrompt:
    """get_agent_system_prompt のテスト."""

    def test_ベースプロンプトが含まれる(self):
        result = get_agent_system_prompt(_make_agent_data())
        assert "馬券会議AI" in result
        assert "## 重要なルール" in result

    def test_エージェント固有のプロンプトが含まれる(self):
        result = get_agent_system_prompt(_make_agent_data(name="テスト太郎"))
        assert "テスト太郎" in result
        assert "堅実型" in result

    def test_キャラクタープロンプトは含まれない(self):
        result = get_agent_system_prompt(_make_agent_data())
        # 旧キャラクタープロンプトの「データ分析官」「直感の達人」等は含まれない
        assert "あなたのキャラクター: データ分析官" not in result
        assert "あなたのキャラクター: 直感の達人" not in result

    def test_ベースプロンプトとエージェントプロンプトが結合されている(self):
        result = get_agent_system_prompt(_make_agent_data())
        # ベースプロンプトの末尾付近とエージェントプロンプトの先頭付近が含まれる
        assert "## あなたのアイデンティティ" in result
        assert "あなたのステータス" in result
