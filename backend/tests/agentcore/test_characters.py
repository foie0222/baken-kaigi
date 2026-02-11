"""agentcore/prompts/characters.py のテスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentcore.prompts.characters import (
    CHARACTER_PROMPTS,
    DEFAULT_CHARACTER,
    get_all_characters,
    get_character_info,
    get_character_prompt,
)
from agentcore.prompts.consultation import SYSTEM_PROMPT, get_system_prompt


class Testキャラクター定義:
    """CHARACTER_PROMPTSの定義を検証する."""

    def test_4種類のキャラクターが定義されている(self):
        assert len(CHARACTER_PROMPTS) == 4
        assert "analyst" in CHARACTER_PROMPTS
        assert "intuition" in CHARACTER_PROMPTS
        assert "conservative" in CHARACTER_PROMPTS
        assert "aggressive" in CHARACTER_PROMPTS

    def test_各キャラクターにname_icon_promptが存在(self):
        for cid, char in CHARACTER_PROMPTS.items():
            assert "name" in char, f"{cid}: name missing"
            assert "icon" in char, f"{cid}: icon missing"
            assert "system_prompt_addition" in char, f"{cid}: system_prompt_addition missing"

    def test_デフォルトキャラクターはanalyst(self):
        assert DEFAULT_CHARACTER == "analyst"

    def test_各キャラクターのプロンプトは空でない(self):
        for cid, char in CHARACTER_PROMPTS.items():
            assert len(char["system_prompt_addition"].strip()) > 0, f"{cid}: prompt is empty"


class Testキャラクター名:
    """キャラクター名の検証."""

    def test_データ分析官(self):
        assert CHARACTER_PROMPTS["analyst"]["name"] == "データ分析官"

    def test_直感の達人(self):
        assert CHARACTER_PROMPTS["intuition"]["name"] == "直感の達人"

    def test_堅実派アドバイザー(self):
        assert CHARACTER_PROMPTS["conservative"]["name"] == "堅実派アドバイザー"

    def test_勝負師(self):
        assert CHARACTER_PROMPTS["aggressive"]["name"] == "勝負師"


class Test_get_character_prompt:
    """get_character_prompt関数のテスト."""

    def test_analystのプロンプトを取得(self):
        prompt = get_character_prompt("analyst")
        assert "データ分析官" in prompt
        assert "統計データ" in prompt

    def test_intuitionのプロンプトを取得(self):
        prompt = get_character_prompt("intuition")
        assert "直感の達人" in prompt
        assert "パドック" in prompt

    def test_conservativeのプロンプトを取得(self):
        prompt = get_character_prompt("conservative")
        assert "堅実派アドバイザー" in prompt
        assert "リスク管理" in prompt

    def test_aggressiveのプロンプトを取得(self):
        prompt = get_character_prompt("aggressive")
        assert "勝負師" in prompt
        assert "高配当" in prompt

    def test_無効なIDはデフォルトにフォールバック(self):
        prompt = get_character_prompt("invalid_character")
        default_prompt = get_character_prompt(DEFAULT_CHARACTER)
        assert prompt == default_prompt

    def test_空文字はデフォルトにフォールバック(self):
        prompt = get_character_prompt("")
        default_prompt = get_character_prompt(DEFAULT_CHARACTER)
        assert prompt == default_prompt


class Test_get_character_info:
    """get_character_info関数のテスト."""

    def test_analystの情報取得(self):
        info = get_character_info("analyst")
        assert info["id"] == "analyst"
        assert info["name"] == "データ分析官"
        assert info["icon"] is not None

    def test_全キャラクターの情報取得(self):
        for cid in CHARACTER_PROMPTS:
            info = get_character_info(cid)
            assert info["id"] == cid
            assert "name" in info
            assert "icon" in info

    def test_無効なIDはデフォルト情報を返す(self):
        info = get_character_info("unknown")
        assert info["id"] == "unknown"
        assert info["name"] == CHARACTER_PROMPTS[DEFAULT_CHARACTER]["name"]


class Test_get_all_characters:
    """get_all_characters関数のテスト."""

    def test_4件のリストを返す(self):
        chars = get_all_characters()
        assert len(chars) == 4

    def test_各要素にid_name_iconが含まれる(self):
        chars = get_all_characters()
        for c in chars:
            assert "id" in c
            assert "name" in c
            assert "icon" in c

    def test_リストの順序はanalyst_intuition_conservative_aggressive(self):
        chars = get_all_characters()
        ids = [c["id"] for c in chars]
        assert ids == ["analyst", "intuition", "conservative", "aggressive"]


class Test_get_system_prompt:
    """get_system_prompt関数のテスト."""

    def test_デフォルトでanalystプロンプトを結合(self):
        prompt = get_system_prompt()
        assert "馬券会議AI" in prompt
        assert "データ分析官" in prompt

    def test_キャラクター指定でプロンプトを結合(self):
        prompt = get_system_prompt("aggressive")
        assert "馬券会議AI" in prompt
        assert "勝負師" in prompt

    def test_ベースプロンプトの重要ルールが維持される(self):
        for cid in CHARACTER_PROMPTS:
            prompt = get_system_prompt(cid)
            assert "**推奨禁止**" in prompt
            assert "**促進禁止**" in prompt
            assert "**判断委任**" in prompt

    def test_ベースプロンプトの6ツールフローが維持される(self):
        for cid in CHARACTER_PROMPTS:
            prompt = get_system_prompt(cid)
            assert "絶対に全6ツールを呼び出すこと（省略厳禁）" in prompt

    def test_キャラクタープロンプトがベースプロンプトの後に追加される(self):
        prompt = get_system_prompt("intuition")
        base_end_pos = prompt.find("直感の達人")
        assert base_end_pos > len(SYSTEM_PROMPT) - 100  # ベースプロンプト末尾付近以降にある

    def test_無効なキャラクターはデフォルトにフォールバック(self):
        prompt = get_system_prompt("nonexistent")
        default_prompt = get_system_prompt(DEFAULT_CHARACTER)
        assert prompt == default_prompt
